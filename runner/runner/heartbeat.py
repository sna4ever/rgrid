"""
Heartbeat management for dead worker detection (Story NEW-7).

Provides:
- HeartbeatManager: Sends periodic heartbeats from worker to database
- DeadWorkerCleaner: Detects stale workers and marks their jobs as failed
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Manages worker heartbeat to detect dead workers.

    Sends periodic heartbeats to the database to signal worker is alive.
    """

    def __init__(
        self,
        worker_id: str,
        hostname: str,
        interval: float = 30.0,
    ):
        """
        Initialize heartbeat manager.

        Args:
            worker_id: Unique worker identifier
            hostname: Worker hostname
            interval: Heartbeat interval in seconds (default: 30)
        """
        self.worker_id = worker_id
        self.hostname = hostname
        self.interval = interval
        self.running = False

    async def send_heartbeat(self, session: AsyncSession) -> None:
        """
        Send a single heartbeat to the database.

        Uses INSERT ... ON CONFLICT to upsert the heartbeat record.

        Args:
            session: Database session
        """
        try:
            # Upsert heartbeat record
            await session.execute(
                text("""
                    INSERT INTO worker_heartbeats (worker_id, last_heartbeat_at)
                    VALUES (:worker_id, :now)
                    ON CONFLICT (worker_id)
                    DO UPDATE SET last_heartbeat_at = :now
                """),
                {
                    "worker_id": self.worker_id,
                    "now": datetime.utcnow(),
                }
            )
            logger.debug(f"Heartbeat sent: {self.worker_id}")

        except Exception as e:
            # Don't crash worker if heartbeat fails
            logger.error(f"Heartbeat failed for {self.worker_id}: {e}")

    async def start_heartbeat_loop(self, session_factory) -> None:
        """
        Start the heartbeat loop that runs periodically.

        Args:
            session_factory: Async session maker for database connections
        """
        self.running = True
        logger.info(f"Starting heartbeat loop for {self.worker_id} (interval={self.interval}s)")

        try:
            while self.running:
                try:
                    async with session_factory() as session:
                        await self.send_heartbeat(session)
                        await session.commit()
                except Exception as e:
                    logger.error(f"Heartbeat loop error: {e}")

                # Wait before next heartbeat
                await asyncio.sleep(self.interval)

        except asyncio.CancelledError:
            logger.info(f"Heartbeat loop cancelled for {self.worker_id}")
        finally:
            logger.info(f"Heartbeat loop stopped for {self.worker_id}")

    def stop_heartbeat_loop(self) -> None:
        """Stop the heartbeat loop."""
        self.running = False


class DeadWorkerCleaner:
    """
    Detects and cleans up dead workers.

    Finds workers with stale heartbeats and marks their running jobs as failed.
    """

    def __init__(
        self,
        stale_threshold_minutes: int = 2,
        check_interval: float = 60.0,
    ):
        """
        Initialize dead worker cleaner.

        Args:
            stale_threshold_minutes: Minutes without heartbeat to consider worker dead (default: 2)
            check_interval: Seconds between cleanup checks (default: 60)
        """
        self.stale_threshold_minutes = stale_threshold_minutes
        self.check_interval = check_interval
        self.running = False

    async def find_stale_workers(self, session: AsyncSession) -> List[Any]:
        """
        Find workers with stale heartbeats (no heartbeat in threshold minutes).

        Args:
            session: Database session

        Returns:
            List of worker heartbeat records (as Row objects) for stale workers
        """
        stale_threshold = datetime.utcnow() - timedelta(minutes=self.stale_threshold_minutes)

        result = await session.execute(
            text("""
                SELECT worker_id, last_heartbeat_at
                FROM worker_heartbeats
                WHERE last_heartbeat_at < :threshold
            """),
            {"threshold": stale_threshold}
        )
        return list(result.fetchall())

    async def mark_jobs_failed(self, session: AsyncSession, worker_id: str) -> int:
        """
        Mark all running jobs from a dead worker as failed.

        Args:
            session: Database session
            worker_id: Worker ID that died

        Returns:
            Number of jobs marked as failed
        """
        result = await session.execute(
            text("""
                UPDATE executions
                SET
                    status = 'failed',
                    execution_error = 'Worker died unexpectedly',
                    completed_at = :now
                WHERE worker_id = :worker_id
                AND status = 'running'
            """),
            {
                "worker_id": worker_id,
                "now": datetime.utcnow(),
            }
        )
        return result.rowcount

    async def cleanup_dead_workers(self, session: AsyncSession) -> int:
        """
        Find dead workers and mark their jobs as failed.

        Args:
            session: Database session

        Returns:
            Number of jobs marked as failed
        """
        total_jobs_failed = 0

        try:
            # Find stale workers
            stale_workers = await self.find_stale_workers(session)

            if stale_workers:
                logger.warning(f"Found {len(stale_workers)} dead workers")

            # Mark jobs as failed for each dead worker
            for worker_row in stale_workers:
                worker_id = worker_row.worker_id  # Access as Row attribute
                jobs_failed = await self.mark_jobs_failed(session, worker_id)

                if jobs_failed > 0:
                    logger.warning(
                        f"Dead worker detected: {worker_id} - marked {jobs_failed} jobs as failed"
                    )
                    total_jobs_failed += jobs_failed

        except Exception as e:
            logger.error(f"Error during dead worker cleanup: {e}", exc_info=True)

        return total_jobs_failed

    async def start_cleanup_loop(self, session_factory) -> None:
        """
        Start the cleanup loop that runs periodically.

        Args:
            session_factory: Async session maker for database connections
        """
        self.running = True
        logger.info(
            f"Starting dead worker cleanup loop "
            f"(threshold={self.stale_threshold_minutes}min, interval={self.check_interval}s)"
        )

        try:
            while self.running:
                try:
                    async with session_factory() as session:
                        jobs_failed = await self.cleanup_dead_workers(session)
                        await session.commit()

                        if jobs_failed > 0:
                            logger.info(f"Cleanup cycle: {jobs_failed} jobs marked as failed")

                except Exception as e:
                    # Don't crash the daemon on errors
                    logger.error(f"Cleanup loop error: {e}", exc_info=True)

                # Wait before next check
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        finally:
            logger.info("Cleanup loop stopped")

    def stop_cleanup_loop(self) -> None:
        """Stop the cleanup loop."""
        self.running = False
