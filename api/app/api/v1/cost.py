"""Cost tracking API endpoints (Story 9-3).

Provides cost breakdown and aggregation endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from pydantic import BaseModel

from app.database import get_db
from app.api.v1.auth import verify_api_key
from app.models.execution import Execution

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
