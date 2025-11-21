"""
Orchestrator daemon for RGrid.

Manages worker health, provisioning, and lifecycle.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from orchestrator.health_monitor import WorkerHealthMonitor
from orchestrator.provisioner import WorkerProvisioner
from orchestrator.lifecycle_manager import WorkerLifecycleManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OrchestratorDaemon:
    """Main orchestrator daemon."""

    def __init__(
        self,
        database_url: str,
        hetzner_api_token: str,
        hetzner_ssh_key_path: str,
        network_id: Optional[int] = None,
        private_db_ip: Optional[str] = None,
    ):
        """
        Initialize orchestrator daemon.

        Args:
            database_url: Database connection string
            hetzner_api_token: Hetzner Cloud API token
            hetzner_ssh_key_path: Path to SSH private key
            network_id: Optional Hetzner private network ID
            private_db_ip: Optional private IP for database
        """
        self.database_url = database_url
        self.hetzner_api_token = hetzner_api_token
        self.hetzner_ssh_key_path = hetzner_ssh_key_path
        self.network_id = network_id
        self.private_db_ip = private_db_ip

        # Components
        self.health_monitor = WorkerHealthMonitor(database_url)
        self.provisioner = WorkerProvisioner(
            database_url, hetzner_api_token, hetzner_ssh_key_path,
            network_id=network_id, private_db_ip=private_db_ip
        )
        self.lifecycle_manager = WorkerLifecycleManager(
            database_url, hetzner_api_token
        )

        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        """Start the orchestrator daemon."""
        logger.info("Starting RGrid Orchestrator Daemon...")
        self._running = True

        # Start all components
        tasks = [
            asyncio.create_task(self.health_monitor.start(), name="health_monitor"),
            asyncio.create_task(self.provisioner.start(), name="provisioner"),
            asyncio.create_task(self.lifecycle_manager.start(), name="lifecycle_manager"),
        ]
        self._tasks = tasks

        logger.info("Orchestrator daemon started successfully")

        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Orchestrator daemon cancelled")
        except Exception as e:
            logger.error(f"Error in orchestrator daemon: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def stop(self):
        """Stop the orchestrator daemon."""
        logger.info("Stopping orchestrator daemon...")
        self._running = False

        # Stop all components
        await self.health_monitor.stop()
        await self.provisioner.stop()
        await self.lifecycle_manager.stop()

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        logger.info("Orchestrator daemon stopped")

    async def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down orchestrator daemon...")
        await self.health_monitor.shutdown()
        await self.provisioner.shutdown()
        await self.lifecycle_manager.shutdown()
        logger.info("Orchestrator daemon shutdown complete")


async def main():
    """Main entry point."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    hetzner_api_token = os.getenv("HETZNER_API_TOKEN")
    hetzner_ssh_key_path = os.getenv("HETZNER_SSH_KEY_PATH")
    network_id = os.getenv("RGRID_NETWORK_ID")  # Optional
    private_db_ip = os.getenv("RGRID_PRIVATE_DB_IP")  # Optional (e.g., "10.0.1.2")

    if not database_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    if not hetzner_api_token:
        logger.error("HETZNER_API_TOKEN not set")
        sys.exit(1)

    if not hetzner_ssh_key_path:
        logger.error("HETZNER_SSH_KEY_PATH not set")
        sys.exit(1)

    # Parse network_id to int if provided
    network_id_int = int(network_id) if network_id else None

    # Log network configuration
    if network_id_int and private_db_ip:
        logger.info(f"Private network enabled (Network ID: {network_id_int}, DB IP: {private_db_ip})")
    else:
        logger.warning("Private network NOT configured - workers will use public database access")

    # Create daemon
    daemon = OrchestratorDaemon(
        database_url=database_url,
        hetzner_api_token=hetzner_api_token,
        hetzner_ssh_key_path=hetzner_ssh_key_path,
        network_id=network_id_int,
        private_db_ip=private_db_ip,
    )

    # Handle signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start daemon
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
