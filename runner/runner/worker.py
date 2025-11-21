"""
RGrid Worker Daemon.

Polls the database for queued executions and processes them.
"""

import asyncio
import logging
import signal
import sys
import uuid
import socket
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from runner.executor import DockerExecutor
from runner.poller import JobPoller
from runner.storage import minio_client
from runner.heartbeat import HeartbeatManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Output size limit (100KB)
OUTPUT_SIZE_LIMIT = 100 * 1024


class Worker:
    """
    Worker daemon that processes queued executions.
    """

    def __init__(
        self,
        database_url: str,
        poll_interval: int = 5,
        max_concurrent: int = 2,
        worker_id: Optional[str] = None,
    ):
        """
        Initialize worker.

        Args:
            database_url: PostgreSQL connection string
            poll_interval: Seconds between polls
            max_concurrent: Maximum concurrent executions
            worker_id: Unique worker ID (auto-generated if not provided)
        """
        self.database_url = database_url
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self.active_tasks = set()

        # Generate worker ID if not provided
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.hostname = socket.gethostname()

        # Create async engine
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Docker executor
        self.executor = DockerExecutor()

        # Job poller
        self.poller = JobPoller(self.async_session_maker)

        # Heartbeat manager (Story NEW-7)
        self.heartbeat_manager = HeartbeatManager(
            worker_id=self.worker_id,
            hostname=self.hostname,
            interval=30,
        )
        self.heartbeat_task = None

    async def start(self):
        """Start the worker daemon."""
        logger.info(f"Starting RGrid worker {self.worker_id} (max_concurrent={self.max_concurrent})")
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Start heartbeat loop (Story NEW-7)
        self.heartbeat_task = asyncio.create_task(
            self.heartbeat_manager.start_heartbeat_loop(self.async_session_maker)
        )
        logger.info(f"Heartbeat loop started for {self.worker_id}")

        try:
            while self.running:
                # Check if we can accept more jobs
                if len(self.active_tasks) < self.max_concurrent:
                    job = await self.poller.claim_next_job()
                    if job:
                        logger.info(f"Claimed job: {job.execution_id}")
                        # Start processing in background
                        task = asyncio.create_task(self.process_job(job))
                        self.active_tasks.add(task)
                        task.add_done_callback(self.active_tasks.discard)
                    else:
                        # No jobs available, wait before polling again
                        await asyncio.sleep(self.poll_interval)
                else:
                    # At capacity, wait
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def process_job(self, job):
        """
        Process a single execution.

        Args:
            job: Execution database record
        """
        execution_id = job.execution_id
        logger.info(f"Processing {execution_id}: {job.runtime}")

        try:
            # Track start time for duration calculation (Story 8.6)
            started_at = datetime.utcnow()

            # Update status to running
            async with self.async_session_maker() as session:
                await self.poller.update_status(
                    session, execution_id, "running", started_at=started_at
                )
                await session.commit()

            # Generate download URLs for input files (Tier 4 - Story 2-5)
            download_urls = {}
            input_files = job.input_files or []

            if input_files:
                for filename in input_files:
                    object_key = f"executions/{execution_id}/inputs/{filename}"
                    download_url = minio_client.generate_presigned_download_url(
                        object_key, expiration=3600
                    )
                    download_urls[filename] = download_url

            # Execute script using DockerExecutor
            # Story 2.4: Pass requirements_content for auto-installing Python deps
            exit_code, stdout, stderr, uploaded_outputs = self.executor.execute_script(
                script_content=job.script_content,
                runtime=job.runtime,
                args=job.args or [],
                env_vars=job.env_vars or {},
                download_urls=download_urls if download_urls else None,
                requirements_content=getattr(job, 'requirements_content', None),
            )

            # Truncate output if too large
            output_truncated = False
            if len(stdout) > OUTPUT_SIZE_LIMIT:
                stdout = stdout[:OUTPUT_SIZE_LIMIT]
                output_truncated = True
                logger.warning(f"{execution_id}: stdout truncated (>{OUTPUT_SIZE_LIMIT} bytes)")

            if len(stderr) > OUTPUT_SIZE_LIMIT:
                stderr = stderr[:OUTPUT_SIZE_LIMIT]
                output_truncated = True
                logger.warning(f"{execution_id}: stderr truncated (>{OUTPUT_SIZE_LIMIT} bytes)")

            # Determine final status
            final_status = "completed" if exit_code == 0 else "failed"

            # Calculate completion time and duration (Story 8.6)
            completed_at = datetime.utcnow()
            duration_seconds = int((completed_at - started_at).total_seconds())

            # Build execution metadata (Story 8.6)
            execution_metadata = {
                "runtime": job.runtime,
                "env_vars_count": str(len(job.env_vars or {})),
                "input_files_count": str(len(job.input_files or [])),
                "worker_id": self.worker_id,
            }

            # Update database with results
            async with self.async_session_maker() as session:
                await self.poller.update_execution_result(
                    session=session,
                    execution_id=execution_id,
                    status=final_status,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    output_truncated=output_truncated,
                    completed_at=completed_at,
                    duration_seconds=duration_seconds,
                    worker_hostname=self.hostname,
                    execution_metadata=execution_metadata,
                )
                await session.commit()

            logger.info(f"Completed {execution_id}: exit_code={exit_code}, status={final_status}, duration={duration_seconds}s")

        except Exception as e:
            logger.error(f"Error processing {execution_id}: {e}", exc_info=True)

            # Mark as failed
            try:
                async with self.async_session_maker() as session:
                    await self.poller.update_execution_result(
                        session=session,
                        execution_id=execution_id,
                        status="failed",
                        execution_error=str(e),
                        completed_at=datetime.utcnow(),
                    )
                    await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error status for {execution_id}: {update_error}")

    async def shutdown(self):
        """Gracefully shutdown worker."""
        logger.info("Shutting down worker...")
        self.running = False

        # Stop heartbeat loop (Story NEW-7)
        if self.heartbeat_task:
            logger.info("Stopping heartbeat loop...")
            self.heartbeat_manager.stop_heartbeat_loop()
            try:
                await asyncio.wait_for(self.heartbeat_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Heartbeat task did not stop cleanly")
                self.heartbeat_task.cancel()

        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks...")
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

        # Close Docker executor
        self.executor.close()

        # Close database engine
        await self.engine.dispose()

        logger.info("Worker shut down complete")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


async def main():
    """Main entry point."""
    import os

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Ensure it uses asyncpg driver
    if "postgresql://" in database_url and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create and start worker
    worker = Worker(
        database_url=database_url,
        poll_interval=5,
        max_concurrent=2,
    )

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
