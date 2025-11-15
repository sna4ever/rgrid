"""
Health check endpoint.

Provides system health status for monitoring and load balancers.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from rgrid_common.models import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns system status and version information.
    Also verifies database connectivity.

    Returns:
        HealthCheckResponse: Health status
    """
    # Test database connection
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthCheckResponse(
        status=f"ok (db: {db_status})",
        version="0.1.0",
        timestamp=datetime.utcnow(),
    )
