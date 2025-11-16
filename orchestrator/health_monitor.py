"""Worker health monitoring for RGrid orchestrator (Tier 4 - Story 3-4)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update, and_

logger = logging.getLogger(__name__)

# Constants
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 120  # seconds (2 minutes)
MONITOR_INTERVAL = 30  # seconds


class WorkerHealthMonitor:
    """Monitor worker heartbeats and detect dead workers."""

    def __init__(self, database_url: str):
        """
        Initialize health monitor.

        Args:
            database_url: Database connection string
        """
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._running = False

    async def start(self):
        """Start the health monitoring loop."""
        self._running = True
        logger.info("Worker health monitor started")

        try:
            while self._running:
                await self.check_worker_heartbeats()
                await asyncio.sleep(MONITOR_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Worker health monitor cancelled")
        except Exception as e:
            logger.error(f"Error in health monitor loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def stop(self):
        """Stop the health monitoring loop."""
        self._running = False
        logger.info("Worker health monitor stopped")

    async def shutdown(self):
        """Clean up resources."""
        await self.engine.dispose()

    async def check_worker_heartbeats(self):
        """Check all worker heartbeats and mark dead workers."""
        from api.app.models.worker import Worker, WorkerHeartbeat

        async with self.async_session_maker() as session:
            # Calculate deadline for heartbeat
            deadline = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT)

            # Find workers with stale heartbeats
            query = (
                select(Worker, WorkerHeartbeat)
                .join(WorkerHeartbeat, Worker.worker_id == WorkerHeartbeat.worker_id)
                .where(
                    and_(
                        Worker.status == 'active',
                        WorkerHeartbeat.last_heartbeat_at < deadline
                    )
                )
            )

            result = await session.execute(query)
            dead_workers = result.all()

            if dead_workers:
                logger.warning(f"Found {len(dead_workers)} dead workers")

                for worker, heartbeat in dead_workers:
                    await self.handle_dead_worker(session, worker.worker_id, heartbeat.last_heartbeat_at)

                await session.commit()
            else:
                logger.debug(f"All workers healthy (checked at {datetime.utcnow()})")

    async def handle_dead_worker(
        self,
        session: AsyncSession,
        worker_id: str,
        last_heartbeat: datetime
    ):
        """
        Handle a dead worker.

        Args:
            session: Database session
            worker_id: Worker ID
            last_heartbeat: Last heartbeat timestamp
        """
        from api.app.models.worker import Worker
        from api.app.models.execution import Execution

        logger.warning(
            f"Worker {worker_id} is dead (last heartbeat: {last_heartbeat})"
        )

        # Mark worker as dead
        await session.execute(
            update(Worker)
            .where(Worker.worker_id == worker_id)
            .values(
                status='dead',
                terminated_at=datetime.utcnow()
            )
        )

        # Find orphaned executions
        orphaned_query = select(Execution).where(
            and_(
                Execution.worker_id == worker_id,
                Execution.status.in_(['queued', 'running'])
            )
        )
        result = await session.execute(orphaned_query)
        orphaned_executions = result.scalars().all()

        if orphaned_executions:
            logger.info(
                f"Found {len(orphaned_executions)} orphaned executions from worker {worker_id}"
            )

            # Reschedule orphaned executions
            for execution in orphaned_executions:
                await self.reschedule_execution(session, execution)

        logger.info(f"Worker {worker_id} marked as dead and cleaned up")

    async def reschedule_execution(self, session: AsyncSession, execution):
        """
        Reschedule an orphaned execution.

        Args:
            session: Database session
            execution: Execution record
        """
        from api.app.models.execution import Execution

        logger.info(
            f"Rescheduling execution {execution.execution_id} "
            f"(was on dead worker {execution.worker_id})"
        )

        # Reset execution to queued state
        await session.execute(
            update(Execution)
            .where(Execution.execution_id == execution.execution_id)
            .values(
                status='queued',
                worker_id=None,
                ray_task_id=None,
                started_at=None,
                execution_error=f"Worker {execution.worker_id} died - rescheduled"
            )
        )

        # Note: The Ray task will need to be resubmitted by the API
        # when the execution is picked up again


class WorkerHeartbeatSender:
    """Send periodic heartbeats from worker to database."""

    def __init__(self, worker_id: str, database_url: str):
        """
        Initialize heartbeat sender.

        Args:
            worker_id: Worker ID
            database_url: Database connection string
        """
        self.worker_id = worker_id
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._running = False

    async def start(self):
        """Start sending heartbeats."""
        self._running = True
        logger.info(f"Heartbeat sender started for worker {self.worker_id}")

        try:
            while self._running:
                await self.send_heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            logger.info(f"Heartbeat sender cancelled for worker {self.worker_id}")
        except Exception as e:
            logger.error(f"Error in heartbeat sender: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def stop(self):
        """Stop sending heartbeats."""
        self._running = False
        logger.info(f"Heartbeat sender stopped for worker {self.worker_id}")

    async def shutdown(self):
        """Clean up resources."""
        await self.engine.dispose()

    async def send_heartbeat(self):
        """Send a heartbeat to the database."""
        from api.app.models.worker import WorkerHeartbeat
        from sqlalchemy.dialects.postgresql import insert

        try:
            async with self.async_session_maker() as session:
                # Upsert heartbeat record
                stmt = insert(WorkerHeartbeat).values(
                    worker_id=self.worker_id,
                    last_heartbeat_at=datetime.utcnow(),
                    ray_available_resources=None  # TODO: Get from Ray
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['worker_id'],
                    set_={
                        'last_heartbeat_at': datetime.utcnow(),
                        'ray_available_resources': None
                    }
                )

                await session.execute(stmt)
                await session.commit()

                logger.debug(f"Heartbeat sent for worker {self.worker_id}")

        except Exception as e:
            logger.error(f"Failed to send heartbeat for worker {self.worker_id}: {e}")
