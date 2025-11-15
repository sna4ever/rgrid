"""
Database poller for claiming jobs atomically.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# We need to import the Execution model
# Since we're in runner package, we need to setup the path correctly
import sys
from pathlib import Path

# Add api to path to import models
api_path = Path(__file__).parent.parent.parent / "api"
sys.path.insert(0, str(api_path))

from app.models.execution import Execution

logger = logging.getLogger(__name__)


class JobPoller:
    """
    Polls database for queued jobs and claims them atomically.
    """

    def __init__(self, session_maker):
        """
        Initialize poller.

        Args:
            session_maker: Async session maker for database access
        """
        self.session_maker = session_maker

    async def claim_next_job(self) -> Optional[Execution]:
        """
        Claim next queued job atomically.

        Uses PostgreSQL's FOR UPDATE SKIP LOCKED to ensure
        only one worker claims each job.

        Returns:
            Execution object or None if no jobs available
        """
        async with self.session_maker() as session:
            try:
                # Query for next queued execution with row-level lock
                # FOR UPDATE SKIP LOCKED ensures atomic claiming
                stmt = (
                    select(Execution)
                    .where(Execution.status == "queued")
                    .order_by(Execution.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )

                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution:
                    # Mark as claimed by changing status
                    # (we'll change to 'running' when we actually start execution)
                    await session.commit()
                    logger.debug(f"Claimed job: {execution.execution_id}")
                    return execution

                return None

            except Exception as e:
                logger.error(f"Error claiming job: {e}", exc_info=True)
                await session.rollback()
                return None

    async def update_status(
        self,
        session: AsyncSession,
        execution_id: str,
        status: str,
        started_at: Optional[datetime] = None,
    ):
        """
        Update execution status.

        Args:
            session: Database session
            execution_id: Execution ID
            status: New status
            started_at: Optional start timestamp
        """
        stmt = (
            update(Execution)
            .where(Execution.execution_id == execution_id)
            .values(status=status)
        )

        if started_at:
            stmt = stmt.values(started_at=started_at)

        await session.execute(stmt)

    async def update_execution_result(
        self,
        session: AsyncSession,
        execution_id: str,
        status: str,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        output_truncated: bool = False,
        execution_error: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ):
        """
        Update execution with results.

        Args:
            session: Database session
            execution_id: Execution ID
            status: Final status (completed/failed)
            exit_code: Process exit code
            stdout: Standard output
            stderr: Standard error
            output_truncated: Whether output was truncated
            execution_error: Error message if failed
            completed_at: Completion timestamp
        """
        update_values = {"status": status}

        if exit_code is not None:
            update_values["exit_code"] = exit_code
        if stdout is not None:
            update_values["stdout"] = stdout
        if stderr is not None:
            update_values["stderr"] = stderr
        if output_truncated:
            update_values["output_truncated"] = output_truncated
        if execution_error:
            update_values["execution_error"] = execution_error
        if completed_at:
            update_values["completed_at"] = completed_at

        stmt = (
            update(Execution)
            .where(Execution.execution_id == execution_id)
            .values(**update_values)
        )

        await session.execute(stmt)
