"""Cost tracking API endpoints (Story 9-3, 9-4, 9-5).

Provides cost breakdown, aggregation, estimation, and spending limit endpoints.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.v1.auth import verify_api_key
from app.models.execution import Execution
from app.models.spending_limit import SpendingLimit

# Import estimation functions from orchestrator (Story 9-4)
import sys
import os

# Add orchestrator to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from orchestrator.cost import (
    estimate_batch_cost,
    CX22_HOURLY_COST_MICROS,
    DEFAULT_ESTIMATE_DURATION_SECONDS,
)

# MICRONS pattern constants (same as orchestrator/cost.py)
MICROS_PER_EURO: int = 1_000_000


def format_cost_display(cost_micros: int) -> str:
    """Format cost in microns for human-readable display."""
    euros = cost_micros / MICROS_PER_EURO
    return f"€{euros:.2f}"

logger = logging.getLogger(__name__)
router = APIRouter()


class DailyCost(BaseModel):
    """Cost breakdown for a single day."""
    date: str  # YYYY-MM-DD
    executions: int
    compute_time_seconds: int
    cost_micros: int
    cost_display: str


class CostResponse(BaseModel):
    """Cost breakdown response."""
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    total_cost_micros: int
    total_cost_display: str
    by_date: List[DailyCost]
    total_executions: int


class EstimateResponse(BaseModel):
    """Cost estimation response (Story 9-4)."""
    estimated_executions: int
    estimated_duration_seconds: int
    estimated_total_duration_seconds: int
    estimated_cost_micros: int
    estimated_cost_display: str
    assumptions: List[str]


@router.get("/estimate", response_model=EstimateResponse)
async def get_estimate(
    runtime: str = Query(
        "python:3.11",
        description="Runtime to estimate for (e.g., python:3.11)",
    ),
    files: int = Query(
        1,
        description="Number of files in batch",
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> EstimateResponse:
    """
    Estimate cost for a batch execution (Story 9-4).

    Uses historical execution data to estimate cost based on median duration
    of similar executions. Falls back to a 60s default if no historical data.

    Args:
        runtime: Runtime string to filter historical data (e.g., "python:3.11")
        files: Number of files in the batch
        db: Database session
        api_key: Authenticated API key

    Returns:
        EstimateResponse with cost breakdown and assumptions
    """
    logger.info(f"Estimating cost for {files} files with runtime {runtime}")

    # Query historical executions for the given runtime (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    result = await db.execute(
        select(Execution.duration_seconds)
        .where(Execution.runtime == runtime)
        .where(Execution.status == "completed")
        .where(Execution.duration_seconds.isnot(None))
        .where(Execution.created_at > thirty_days_ago)
        .order_by(Execution.created_at.desc())
        .limit(100)
    )
    rows = result.all()

    # Extract durations
    historical_durations = [row.duration_seconds for row in rows if row.duration_seconds is not None]

    logger.info(f"Found {len(historical_durations)} historical executions for runtime {runtime}")

    # Calculate estimate using orchestrator function
    estimate = estimate_batch_cost(
        file_count=files,
        historical_durations=historical_durations,
        hourly_cost_micros=CX22_HOURLY_COST_MICROS,
    )

    return EstimateResponse(
        estimated_executions=estimate["estimated_executions"],
        estimated_duration_seconds=estimate["estimated_duration_seconds"],
        estimated_total_duration_seconds=estimate["estimated_total_duration_seconds"],
        estimated_cost_micros=estimate["estimated_cost_micros"],
        estimated_cost_display=estimate["estimated_cost_display"],
        assumptions=estimate["assumptions"],
    )


@router.get("/cost", response_model=CostResponse)
async def get_cost(
    since: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD). Default: 7 days ago",
    ),
    until: Optional[str] = Query(
        None,
        description="End date (YYYY-MM-DD). Default: today",
    ),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> CostResponse:
    """
    Get cost breakdown by date.

    Returns daily cost aggregations including execution count,
    compute time, and cost. Uses finalized_cost_micros when
    available, falls back to cost_micros for pending finalization.

    Args:
        since: Start date (YYYY-MM-DD). Default: 7 days ago
        until: End date (YYYY-MM-DD). Default: today
        db: Database session
        api_key: Authenticated API key

    Returns:
        CostResponse with daily breakdown and totals
    """
    # Default date range: last 7 days
    now = datetime.utcnow()
    if not since:
        since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    if not until:
        until = now.strftime("%Y-%m-%d")

    # Parse dates
    start_date = datetime.strptime(since, "%Y-%m-%d")
    # End date should include the full day
    end_date = datetime.strptime(until, "%Y-%m-%d") + timedelta(days=1)

    logger.info(f"Querying cost breakdown: {since} to {until}")

    # Query executions in date range with aggregation by date
    # Use COALESCE to prefer finalized_cost_micros over cost_micros
    result = await db.execute(
        select(
            cast(Execution.created_at, Date).label("date"),
            func.count(Execution.id).label("executions"),
            func.coalesce(func.sum(Execution.duration_seconds), 0).label("compute_time_seconds"),
            func.sum(
                func.coalesce(Execution.finalized_cost_micros, Execution.cost_micros)
            ).label("cost_micros"),
        )
        .where(Execution.created_at >= start_date)
        .where(Execution.created_at < end_date)
        .where(Execution.status.in_(["completed", "failed"]))  # Only count finished executions
        .group_by(cast(Execution.created_at, Date))
        .order_by(cast(Execution.created_at, Date).desc())
    )
    rows = result.all()

    # Build daily cost list
    by_date: List[DailyCost] = []
    total_cost_micros = 0
    total_executions = 0

    for row in rows:
        date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, 'strftime') else str(row.date)
        cost = row.cost_micros or 0
        compute_time = row.compute_time_seconds or 0

        by_date.append(DailyCost(
            date=date_str,
            executions=row.executions,
            compute_time_seconds=compute_time,
            cost_micros=cost,
            cost_display=format_cost_display(cost),
        ))

        total_cost_micros += cost
        total_executions += row.executions

    logger.info(f"Cost breakdown: {total_executions} executions, {format_cost_display(total_cost_micros)}")

    return CostResponse(
        start_date=since,
        end_date=until,
        total_cost_micros=total_cost_micros,
        total_cost_display=format_cost_display(total_cost_micros),
        by_date=by_date,
        total_executions=total_executions,
    )


# ============================================================================
# Story 9-5: Spending Limits and Cost Alerts
# ============================================================================


def hash_api_key(api_key: str) -> str:
    """Create a SHA256 hash of an API key for storage.

    Args:
        api_key: The raw API key

    Returns:
        SHA256 hash of the API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_month_boundaries(now: datetime) -> tuple[datetime, datetime]:
    """Get the start and end of the current billing month.

    Args:
        now: Current date/time

    Returns:
        Tuple of (month_start, next_month_start)
    """
    month_start = datetime(now.year, now.month, 1, 0, 0, 0)
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1, 0, 0, 0)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1, 0, 0, 0)
    return month_start, next_month_start


class SetLimitRequest(BaseModel):
    """Request to set a spending limit."""
    monthly_limit_euros: float = Field(
        ...,
        description="Monthly spending limit in euros (e.g., 50.0 for €50/month)",
        ge=0,
    )


class SpendingLimitResponse(BaseModel):
    """Response with spending limit status."""
    has_limit: bool
    monthly_limit_micros: Optional[int]
    monthly_limit_display: str
    current_usage_micros: int
    current_usage_display: str
    usage_percent: Optional[int]
    status: str  # "ok", "warning", "blocked", "unlimited"
    alert_threshold_percent: int
    message: Optional[str] = None


class LimitSetResponse(BaseModel):
    """Response after setting a limit."""
    success: bool
    monthly_limit_micros: int
    monthly_limit_display: str
    message: str


@router.get("/cost/limit", response_model=SpendingLimitResponse)
async def get_spending_limit(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> SpendingLimitResponse:
    """
    Get current spending limit and usage status (Story 9-5).

    Returns the current monthly spending limit, usage, and status
    (ok, warning at 80%, blocked at 100%, or unlimited if no limit set).

    Args:
        db: Database session
        api_key: Authenticated API key

    Returns:
        SpendingLimitResponse with limit and usage information
    """
    api_key_hash = hash_api_key(api_key)
    now = datetime.utcnow()
    month_start, next_month_start = get_month_boundaries(now)

    # Get spending limit for this API key
    result = await db.execute(
        select(SpendingLimit).where(SpendingLimit.api_key_hash == api_key_hash)
    )
    limit_record = result.scalar_one_or_none()

    # Calculate current month's usage
    usage_result = await db.execute(
        select(
            func.sum(func.coalesce(Execution.finalized_cost_micros, Execution.cost_micros))
        )
        .where(Execution.created_at >= month_start)
        .where(Execution.created_at < next_month_start)
        .where(Execution.status.in_(["completed", "failed"]))
    )
    current_usage_micros = usage_result.scalar() or 0

    # No limit set
    if not limit_record or not limit_record.is_enabled or limit_record.monthly_limit_micros == 0:
        return SpendingLimitResponse(
            has_limit=False,
            monthly_limit_micros=None,
            monthly_limit_display="No limit",
            current_usage_micros=current_usage_micros,
            current_usage_display=format_cost_display(current_usage_micros),
            usage_percent=None,
            status="unlimited",
            alert_threshold_percent=80,
            message="No spending limit configured. Set one with: rgrid cost set-limit <amount>",
        )

    # Calculate percentage and status
    monthly_limit = limit_record.monthly_limit_micros
    usage_percent = (current_usage_micros * 100) // monthly_limit if monthly_limit > 0 else 0

    if usage_percent >= 100:
        status_str = "blocked"
        message = f"Monthly limit exceeded! New executions are blocked. Increase limit or wait until next month."
    elif usage_percent >= limit_record.alert_threshold_percent:
        status_str = "warning"
        message = f"Warning: You've used {usage_percent}% of your monthly limit."
    else:
        status_str = "ok"
        remaining_micros = monthly_limit - current_usage_micros
        message = f"€{remaining_micros / MICROS_PER_EURO:.2f} remaining this month."

    return SpendingLimitResponse(
        has_limit=True,
        monthly_limit_micros=monthly_limit,
        monthly_limit_display=f"€{monthly_limit / MICROS_PER_EURO:.2f}/month",
        current_usage_micros=current_usage_micros,
        current_usage_display=format_cost_display(current_usage_micros),
        usage_percent=usage_percent,
        status=status_str,
        alert_threshold_percent=limit_record.alert_threshold_percent,
        message=message,
    )


@router.put("/cost/limit", response_model=LimitSetResponse)
async def set_spending_limit(
    request: SetLimitRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> LimitSetResponse:
    """
    Set a monthly spending limit (Story 9-5).

    Creates or updates the spending limit for the authenticated API key.
    When usage reaches 80%, a warning is shown. At 100%, new executions
    are blocked.

    Args:
        request: Limit request with monthly_limit_euros
        db: Database session
        api_key: Authenticated API key

    Returns:
        LimitSetResponse confirming the limit was set
    """
    api_key_hash = hash_api_key(api_key)
    monthly_limit_micros = int(request.monthly_limit_euros * MICROS_PER_EURO)

    # Check for existing limit
    result = await db.execute(
        select(SpendingLimit).where(SpendingLimit.api_key_hash == api_key_hash)
    )
    limit_record = result.scalar_one_or_none()

    if limit_record:
        # Update existing
        limit_record.monthly_limit_micros = monthly_limit_micros
        limit_record.is_enabled = True
        limit_record.updated_at = datetime.utcnow()
        # Reset alert timestamps for new limit
        if monthly_limit_micros != limit_record.monthly_limit_micros:
            limit_record.last_80_alert_at = None
            limit_record.last_100_alert_at = None
        logger.info(f"Updated spending limit: €{request.monthly_limit_euros}/month")
    else:
        # Create new
        limit_record = SpendingLimit(
            api_key_hash=api_key_hash,
            monthly_limit_micros=monthly_limit_micros,
            is_enabled=True,
        )
        db.add(limit_record)
        logger.info(f"Created spending limit: €{request.monthly_limit_euros}/month")

    await db.commit()

    return LimitSetResponse(
        success=True,
        monthly_limit_micros=monthly_limit_micros,
        monthly_limit_display=f"€{request.monthly_limit_euros:.2f}/month",
        message=f"Spending limit set to €{request.monthly_limit_euros:.2f}/month. "
                f"You will be warned at 80% and blocked at 100%.",
    )


@router.delete("/cost/limit")
async def remove_spending_limit(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Remove the spending limit (Story 9-5).

    Disables the spending limit for the authenticated API key.
    Usage tracking continues but no warnings or blocking will occur.

    Args:
        db: Database session
        api_key: Authenticated API key

    Returns:
        Success message
    """
    api_key_hash = hash_api_key(api_key)

    result = await db.execute(
        select(SpendingLimit).where(SpendingLimit.api_key_hash == api_key_hash)
    )
    limit_record = result.scalar_one_or_none()

    if limit_record:
        limit_record.is_enabled = False
        limit_record.updated_at = datetime.utcnow()
        await db.commit()
        logger.info("Spending limit removed")
        return {"success": True, "message": "Spending limit removed. No usage limits enforced."}

    return {"success": True, "message": "No spending limit was configured."}
