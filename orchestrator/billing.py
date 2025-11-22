"""
Billing hour cost amortization module (Story 9-2).

Implements fair cost allocation across all jobs in a billing hour:
- When billing hour ends, hourly cost is divided evenly among all jobs
- finalized_cost_micros = hourly_cost_micros / job_count
- Integer arithmetic throughout (no floating point errors)

Cost Fairness Principle:
    All jobs in a billing hour share the hourly cost equally.
    This maximizes cost efficiency when workers process many jobs.

Example:
    Worker hourly cost: EUR 5.83 = 5,830,000 micros
    Jobs in billing hour: 10
    Cost per job: 5,830,000 / 10 = 583,000 micros = EUR 0.58
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def calculate_amortized_cost(hourly_cost_micros: int, job_count: int) -> int:
    """
    Calculate amortized cost per job for a billing hour.

    Divides the hourly worker cost evenly among all jobs in the billing hour.
    Uses integer division (floor) to ensure exact precision.

    Args:
        hourly_cost_micros: Worker hourly cost in micros (e.g., 5,830,000 for CX22)
        job_count: Number of jobs completed in the billing hour

    Returns:
        Cost per job in micros (integer).
        Returns 0 if job_count is 0.

    Example:
        >>> calculate_amortized_cost(5_830_000, 10)
        583000  # EUR 0.58 per job

        >>> calculate_amortized_cost(5_830_000, 1)
        5830000  # Full hourly cost for single job
    """
    if job_count <= 0:
        return 0

    # Integer division (floor) - maintains exact precision
    cost_per_job = hourly_cost_micros // job_count
    return cost_per_job


def get_billing_hour_boundaries(billing_hour_start: datetime) -> Tuple[datetime, datetime]:
    """
    Get billing hour start and end boundaries.

    Args:
        billing_hour_start: Start of the billing hour

    Returns:
        Tuple of (start, end) datetimes
    """
    start = billing_hour_start
    end = billing_hour_start + timedelta(hours=1)
    return start, end


async def finalize_billing_hour_costs(session: AsyncSession, worker) -> int:
    """
    Finalize costs for all executions in a worker's billing hour.

    Called when:
    - Worker is being terminated (before deletion)
    - Billing hour ends and worker is idle

    Algorithm:
    1. Find all completed/failed executions in billing hour
    2. Calculate amortized cost: hourly_cost / job_count
    3. Update each execution with finalized_cost_micros

    Args:
        session: Database session
        worker: Worker record with billing_hour_start and hourly_cost_micros

    Returns:
        Number of executions finalized

    Side effects:
        Updates executions table with finalized_cost_micros and cost_finalized_at
    """
    from api.app.models.execution import Execution

    # Get billing hour boundaries
    if not worker.billing_hour_start:
        logger.warning(f"Worker {worker.worker_id} has no billing_hour_start, using created_at")
        billing_start = worker.created_at
    else:
        billing_start = worker.billing_hour_start

    billing_end = billing_start + timedelta(hours=1)
    hourly_cost = worker.hourly_cost_micros

    logger.info(
        f"Finalizing costs for worker {worker.worker_id} "
        f"billing hour {billing_start} to {billing_end}"
    )

    # Find all completed/failed executions in this billing hour
    # that haven't been finalized yet
    query = select(Execution).where(
        and_(
            Execution.worker_id == worker.worker_id,
            Execution.started_at >= billing_start,
            Execution.started_at < billing_end,
            Execution.status.in_(['completed', 'failed']),
            Execution.finalized_cost_micros.is_(None)  # Not yet finalized
        )
    )
    result = await session.execute(query)
    executions = result.scalars().all()

    if not executions:
        logger.info(f"No unfinalized executions in billing hour for {worker.worker_id}")
        return 0

    # Calculate amortized cost
    job_count = len(executions)
    cost_per_job = calculate_amortized_cost(hourly_cost, job_count)
    total_amortized = cost_per_job * job_count

    logger.info(
        f"Amortizing EUR {hourly_cost / 1_000_000:.2f} across {job_count} jobs: "
        f"EUR {cost_per_job / 1_000_000:.4f} per job "
        f"(total: EUR {total_amortized / 1_000_000:.2f})"
    )

    # Update all executions with finalized cost
    now = datetime.utcnow()
    for execution in executions:
        await session.execute(
            update(Execution)
            .where(Execution.execution_id == execution.execution_id)
            .values(
                finalized_cost_micros=cost_per_job,
                cost_finalized_at=now
            )
        )
        logger.debug(
            f"Finalized execution {execution.execution_id}: "
            f"EUR {cost_per_job / 1_000_000:.4f}"
        )

    logger.info(
        f"Finalized {job_count} executions for worker {worker.worker_id}"
    )

    return job_count
