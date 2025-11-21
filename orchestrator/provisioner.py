"""Worker provisioning logic (Tier 4 - Stories 4-1, 4-2)."""

import asyncio
import logging
import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from orchestrator.hetzner_client import HetznerClient

logger = logging.getLogger(__name__)

# Provisioning constants
PROVISION_CHECK_INTERVAL = 60  # seconds
MIN_QUEUE_DEPTH = 1  # Provision worker if queue >= 1 (provision on ANY queued job)
MAX_WORKERS = 10  # Maximum concurrent workers
WORKER_CONCURRENT_JOBS = 2  # Jobs per worker


class WorkerProvisioner:
    """Manages worker provisioning based on queue depth."""

    def __init__(
        self,
        database_url: str,
        hetzner_api_token: str,
        ssh_key_path: str,
        network_id: Optional[int] = None,
        private_db_ip: Optional[str] = None
    ):
        """
        Initialize provisioner.

        Args:
            database_url: Database connection string
            hetzner_api_token: Hetzner Cloud API token
            ssh_key_path: Path to SSH private key
            network_id: Optional Hetzner private network ID
            private_db_ip: Optional private IP for database (e.g., 10.0.1.2)
        """
        self.database_url = database_url
        self.hetzner_client = HetznerClient(hetzner_api_token)
        self.ssh_key_path = ssh_key_path
        self.network_id = network_id
        self.private_db_ip = private_db_ip
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._running = False
        self._ssh_key_id: Optional[int] = None

    async def start(self):
        """Start provisioning loop."""
        self._running = True
        logger.info("Worker provisioner started")

        # Ensure SSH key exists
        await self._ensure_ssh_key()

        try:
            while self._running:
                await self.check_and_provision()
                await asyncio.sleep(PROVISION_CHECK_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Worker provisioner cancelled")
        except Exception as e:
            logger.error(f"Error in provisioner loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def stop(self):
        """Stop provisioning loop."""
        self._running = False
        logger.info("Worker provisioner stopped")

    async def shutdown(self):
        """Clean up resources."""
        await self.engine.dispose()

    async def _ensure_ssh_key(self):
        """Ensure SSH key exists in Hetzner."""
        try:
            # Check if key already exists
            keys = await self.hetzner_client.get_ssh_keys()
            rgrid_key = next((k for k in keys if k["name"] == "rgrid-worker"), None)

            if rgrid_key:
                self._ssh_key_id = rgrid_key["id"]
                logger.info(f"Using existing SSH key (ID: {self._ssh_key_id})")
            else:
                # Read public key from file
                with open(f"{self.ssh_key_path}.pub", "r") as f:
                    public_key = f.read().strip()

                # Create key
                key = await self.hetzner_client.create_ssh_key("rgrid-worker", public_key)
                self._ssh_key_id = key["id"]
                logger.info(f"Created SSH key (ID: {self._ssh_key_id})")

        except Exception as e:
            logger.error(f"Failed to ensure SSH key: {e}")
            self._ssh_key_id = 1  # Fallback to first key

    async def check_and_provision(self):
        """Check queue depth and provision workers if needed."""
        from api.app.models.execution import Execution
        from api.app.models.worker import Worker

        try:
            async with self.async_session_maker() as session:
                # Get queue depth (queued executions)
                queue_query = select(func.count(Execution.id)).where(
                    Execution.status == 'queued'
                )
                queue_result = await session.execute(queue_query)
                queue_depth = queue_result.scalar() or 0

                # Get active+provisioning worker count
                # Count both 'provisioning' and 'active' to avoid over-provisioning
                worker_query = select(func.count(Worker.worker_id)).where(
                    Worker.status.in_(['active', 'provisioning'])
                )
                worker_result = await session.execute(worker_query)
                active_workers = worker_result.scalar() or 0

                logger.debug(
                    f"Queue depth: {queue_depth}, Active workers: {active_workers}"
                )

                # Calculate needed capacity
                needed_capacity = queue_depth
                current_capacity = active_workers * WORKER_CONCURRENT_JOBS
                available_capacity = current_capacity

                # Get running executions
                running_query = select(func.count(Execution.id)).where(
                    Execution.status == 'running'
                )
                running_result = await session.execute(running_query)
                running_count = running_result.scalar() or 0

                available_capacity -= running_count

                # Decide if we need more workers
                if queue_depth >= MIN_QUEUE_DEPTH and available_capacity < queue_depth:
                    if active_workers < MAX_WORKERS:
                        workers_needed = min(
                            (queue_depth - available_capacity + WORKER_CONCURRENT_JOBS - 1) // WORKER_CONCURRENT_JOBS,
                            MAX_WORKERS - active_workers
                        )

                        logger.info(
                            f"Provisioning {workers_needed} workers "
                            f"(queue: {queue_depth}, capacity: {available_capacity})"
                        )

                        for _ in range(workers_needed):
                            await self.provision_worker(session)

                        await session.commit()
                    else:
                        logger.warning(
                            f"Max workers ({MAX_WORKERS}) reached, cannot provision more"
                        )

        except Exception as e:
            logger.error(f"Error checking queue and provisioning: {e}", exc_info=True)

    async def provision_worker(self, session: AsyncSession, retry_attempt: int = 1) -> Optional[str]:
        """
        Provision a new worker with retry and detailed error handling.

        Args:
            session: Database session
            retry_attempt: Current retry attempt number (1-indexed)

        Returns:
            Worker ID if successful, None otherwise
        """
        from api.app.models.worker import Worker

        # Generate worker ID
        worker_id = f"worker-{secrets.token_hex(8)}"
        server_name = f"rgrid-{worker_id}"

        if retry_attempt > 1:
            logger.info(f"Provisioning worker {worker_id}... (attempt {retry_attempt}/3)")
        else:
            logger.info(f"Provisioning worker {worker_id}... (ETA: ~90 seconds)")

        try:
            # Generate cloud-init user data
            user_data = self._generate_cloud_init(worker_id)

            # Create server via Hetzner API
            networks = [self.network_id] if self.network_id else None

            response = await self.hetzner_client.create_server(
                name=server_name,
                ssh_key_id=self._ssh_key_id,
                user_data=user_data,
                labels={
                    "project": "rgrid",
                    "worker_id": worker_id,
                    "role": "worker",
                },
                networks=networks,
            )

            server = response["server"]
            server_id = server["id"]
            ip_address = server["public_net"]["ipv4"]["ip"]

            # Create worker record in database
            db_worker = Worker(
                worker_id=worker_id,
                node_id=str(server_id),
                ip_address=ip_address,
                max_concurrent=WORKER_CONCURRENT_JOBS,
                status='provisioning',
                created_at=datetime.utcnow(),
            )

            session.add(db_worker)

            logger.info(
                f"Worker {worker_id} provisioned successfully "
                f"(server: {server_id}, IP: {ip_address}). Worker will be ready in ~60 seconds."
            )

            return worker_id

        except Exception as e:
            error_message = str(e).lower()

            # Provide user-friendly error messages based on error type
            if "quota" in error_message or "limit" in error_message:
                logger.error(
                    f"Failed to provision worker {worker_id}: "
                    f"Worker limit reached. Upgrade Hetzner account or wait for workers to free up."
                )
            elif "network" in error_message or "connection" in error_message:
                logger.error(
                    f"Failed to provision worker {worker_id}: "
                    f"Cannot reach cloud provider. Check network connection."
                )
            elif "unauthorized" in error_message or "authentication" in error_message:
                logger.error(
                    f"Failed to provision worker {worker_id}: "
                    f"Hetzner API authentication failed. Check HETZNER_API_TOKEN."
                )
            else:
                logger.error(
                    f"Failed to provision worker {worker_id}: "
                    f"Cloud provider error. {e}"
                )

            # Retry logic (up to 3 attempts)
            if retry_attempt < 3 and "quota" not in error_message:
                logger.info(f"Retrying... (attempt {retry_attempt + 1}/3)")
                await asyncio.sleep(5)  # Wait before retry
                return await self.provision_worker(session, retry_attempt + 1)

            return None

    def _generate_cloud_init(self, worker_id: str) -> str:
        """
        Generate cloud-init user data for worker.

        Uses Docker image approach for faster, more reliable deployment.
        The worker runs as a Docker container with access to host Docker socket
        for executing job containers.

        Args:
            worker_id: Worker ID

        Returns:
            Cloud-init YAML
        """
        # Get database URL (convert to sync for worker)
        db_url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")

        # Use private network IP if available, otherwise public IP
        if self.private_db_ip:
            # Private network - use private IP (secure, no internet exposure)
            db_url = db_url.replace("localhost", self.private_db_ip)
            logger.info(f"Using private network IP for database: {self.private_db_ip}")
        else:
            # Fallback to public IP (less secure, for testing only)
            db_url = db_url.replace("localhost", "46.62.246.120")
            logger.warning("No private network configured - using public IP for database")

        return f"""#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io

runcmd:
  # Pull RGrid worker Docker image from GitHub Container Registry
  # This image contains all runner code and dependencies pre-installed
  - echo "Pulling rgrid-worker image..."
  - docker pull ghcr.io/sna4ever/rgrid-worker:latest

  # Pre-pull common Docker images (Story 4-4 - Performance Optimization)
  # This reduces cold-start latency for first job on worker
  - echo "Pre-pulling common runtime images..."
  - docker pull python:3.11-slim &
  - docker pull python:3.10-slim &
  - docker pull python:3.9-slim &
  - docker pull node:20-slim &
  - docker pull node:18-slim &
  # Wait for pulls to complete (run in background to not block worker startup)
  - wait

  # Start RGrid worker container
  # - Runs in detached mode with auto-restart
  # - Mounts Docker socket for job execution
  # - Mounts /tmp for shared access (Docker-in-Docker volume sharing)
  # - Passes DATABASE_URL and WORKER_ID as environment variables
  - echo "Starting rgrid-worker container..."
  - docker run -d \
      --name rgrid-worker \
      --restart always \
      -e DATABASE_URL={db_url} \
      -e WORKER_ID={worker_id} \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /tmp:/tmp \
      ghcr.io/sna4ever/rgrid-worker:latest

  # Verify worker started successfully
  - sleep 5
  - docker logs rgrid-worker --tail 20
"""
