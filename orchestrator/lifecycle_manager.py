"""Worker lifecycle management (Tier 4 - Stories 4-3, 4-5)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_

from orchestrator.hetzner_client import HetznerClient
from orchestrator.billing import finalize_billing_hour_costs

logger = logging.getLogger(__name__)

# Lifecycle constants
LIFECYCLE_CHECK_INTERVAL = 60  # seconds
BILLING_HOUR_MINUTES = 60  # Hetzner bills per hour
TERMINATION_GRACE_MINUTES = 5  # Terminate 5 min before billing hour
WORKER_MAX_AGE_HOURS = 24  # Maximum worker lifetime


class WorkerLifecycleManager:
    """Manages worker lifecycle, replacement, and billing optimization."""

    def __init__(self, database_url: str, hetzner_api_token: str):
        """
        Initialize lifecycle manager.

        Args:
            database_url: Database connection string
            hetzner_api_token: Hetzner Cloud API token
        """
        self.database_url = database_url
        self.hetzner_client = HetznerClient(hetzner_api_token)
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._running = False

    async def start(self):
        """Start lifecycle management loop."""
        self._running = True
        logger.info("Worker lifecycle manager started")

        try:
            while self._running:
                await self.manage_worker_lifecycle()
                await asyncio.sleep(LIFECYCLE_CHECK_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Worker lifecycle manager cancelled")
        except Exception as e:
            logger.error(f"Error in lifecycle manager loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def stop(self):
        """Stop lifecycle management loop."""
        self._running = False
        logger.info("Worker lifecycle manager stopped")

    async def shutdown(self):
        """Clean up resources."""
        await self.engine.dispose()

    async def manage_worker_lifecycle(self):
        """
        Manage worker lifecycle:
        - Terminate idle workers near billing hour
        - Replace failed workers
        - Terminate aged workers
        """
        try:
            async with self.async_session_maker() as session:
                await self.terminate_idle_workers_near_billing_hour(session)
                await self.replace_failed_workers(session)
                await self.terminate_aged_workers(session)
                await session.commit()

        except Exception as e:
            logger.error(f"Error managing worker lifecycle: {e}", exc_info=True)

    async def terminate_idle_workers_near_billing_hour(self, session: AsyncSession):
        """
        Terminate idle workers that are approaching billing hour (Story 4-3).

        This optimizes costs by avoiding partial hour charges.
        """
        from api.app.models.worker import Worker
        from api.app.models.execution import Execution

        now = datetime.utcnow()

        # Find active workers
        worker_query = select(Worker).where(Worker.status == 'active')
        result = await session.execute(worker_query)
        workers = result.scalars().all()

        for worker in workers:
            # Calculate time until next billing hour
            worker_age = now - worker.created_at
            minutes_since_creation = worker_age.total_seconds() / 60
            minutes_into_hour = minutes_since_creation % BILLING_HOUR_MINUTES
            minutes_until_billing = BILLING_HOUR_MINUTES - minutes_into_hour

            # Check if approaching billing hour
            if minutes_until_billing <= TERMINATION_GRACE_MINUTES:
                # Check if worker is idle
                running_query = select(Execution).where(
                    and_(
                        Execution.worker_id == worker.worker_id,
                        Execution.status.in_(['queued', 'running'])
                    )
                )
                running_result = await session.execute(running_query)
                running_jobs = running_result.scalars().all()

                if not running_jobs:
                    logger.info(
                        f"Terminating idle worker {worker.worker_id} "
                        f"({minutes_until_billing:.1f} min until billing hour)"
                    )
                    await self.terminate_worker(session, worker)
                else:
                    logger.debug(
                        f"Worker {worker.worker_id} has {len(running_jobs)} jobs, "
                        f"not terminating despite billing hour"
                    )

    async def replace_failed_workers(self, session: AsyncSession):
        """
        Replace workers that have failed (Story 4-5).

        When a worker is marked as dead by health monitor,
        this creates a replacement worker.
        """
        from api.app.models.worker import Worker
        from api.app.models.execution import Execution

        # Find recently dead workers (within last 5 minutes)
        recent_threshold = datetime.utcnow() - timedelta(minutes=5)

        dead_worker_query = select(Worker).where(
            and_(
                Worker.status == 'dead',
                Worker.terminated_at >= recent_threshold
            )
        )
        result = await session.execute(dead_worker_query)
        dead_workers = result.scalars().all()

        for worker in dead_workers:
            # Check if there are orphaned jobs
            orphaned_query = select(Execution).where(
                and_(
                    Execution.worker_id == worker.worker_id,
                    Execution.status == 'queued'  # Already rescheduled by health monitor
                )
            )
            orphaned_result = await session.execute(orphaned_query)
            orphaned_jobs = orphaned_result.scalars().all()

            if orphaned_jobs:
                logger.info(
                    f"Worker {worker.worker_id} failed with {len(orphaned_jobs)} jobs, "
                    f"requesting replacement"
                )
                # Note: Provisioner will handle creating new worker based on queue depth
                # We just ensure the dead worker's Hetzner server is deleted
                if worker.node_id:
                    await self.delete_hetzner_server(int(worker.node_id))

    async def terminate_aged_workers(self, session: AsyncSession):
        """
        Terminate workers that exceed maximum age.

        This prevents workers from running indefinitely.
        """
        from api.app.models.worker import Worker
        from api.app.models.execution import Execution

        max_age_threshold = datetime.utcnow() - timedelta(hours=WORKER_MAX_AGE_HOURS)

        aged_worker_query = select(Worker).where(
            and_(
                Worker.status == 'active',
                Worker.created_at <= max_age_threshold
            )
        )
        result = await session.execute(aged_worker_query)
        aged_workers = result.scalars().all()

        for worker in aged_workers:
            # Check if worker is idle
            running_query = select(Execution).where(
                and_(
                    Execution.worker_id == worker.worker_id,
                    Execution.status.in_(['queued', 'running'])
                )
            )
            running_result = await session.execute(running_query)
            running_jobs = running_result.scalars().all()

            if not running_jobs:
                logger.info(
                    f"Terminating aged worker {worker.worker_id} "
                    f"(age: {(datetime.utcnow() - worker.created_at).total_seconds() / 3600:.1f}h)"
                )
                await self.terminate_worker(session, worker)
            else:
                logger.warning(
                    f"Aged worker {worker.worker_id} still has {len(running_jobs)} jobs"
                )

    async def terminate_worker(self, session: AsyncSession, worker):
        """
        Terminate a worker.

        Finalizes billing hour costs before termination (Story 9-2).

        Args:
            session: Database session
            worker: Worker record
        """
        from api.app.models.worker import Worker
        from sqlalchemy import update

        # Finalize billing hour costs before termination (Story 9-2)
        try:
            finalized_count = await finalize_billing_hour_costs(session, worker)
            if finalized_count > 0:
                logger.info(
                    f"Finalized costs for {finalized_count} executions "
                    f"before terminating worker {worker.worker_id}"
                )
        except Exception as e:
            logger.error(
                f"Error finalizing costs for worker {worker.worker_id}: {e}",
                exc_info=True
            )
            # Continue with termination even if cost finalization fails

        # Update worker status
        await session.execute(
            update(Worker)
            .where(Worker.worker_id == worker.worker_id)
            .values(
                status='terminated',
                terminated_at=datetime.utcnow()
            )
        )

        # Delete Hetzner server
        if worker.node_id:
            await self.delete_hetzner_server(int(worker.node_id))

        logger.info(f"Worker {worker.worker_id} terminated")

    async def delete_hetzner_server(self, server_id: int):
        """
        Delete Hetzner server.

        Args:
            server_id: Hetzner server ID
        """
        try:
            await self.hetzner_client.delete_server(server_id)
            logger.info(f"Hetzner server {server_id} deleted")
        except Exception as e:
            logger.error(f"Failed to delete Hetzner server {server_id}: {e}")
