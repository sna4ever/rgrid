"""Execution endpoints."""

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.v1.auth import verify_api_key
from app.models.execution import Execution
from rgrid_common.models import ExecutionCreate, ExecutionResponse
from rgrid_common.types import ExecutionStatus

router = APIRouter()


@router.post("/executions", response_model=ExecutionResponse)
async def create_execution(
    execution: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ExecutionResponse:
    """
    Create a new execution.

    Args:
        execution: Execution details
        db: Database session
        api_key: Authenticated API key

    Returns:
        Created execution
    """
    # Generate execution ID
    execution_id = f"exec_{secrets.token_hex(16)}"

    # Create database record
    runtime_str = execution.runtime.value if hasattr(execution.runtime, 'value') else execution.runtime
    db_execution = Execution(
        execution_id=execution_id,
        script_content=execution.script_content,
        runtime=runtime_str,
        args=execution.args,
        env_vars=execution.env_vars,
        status=ExecutionStatus.QUEUED.value,
        created_at=datetime.utcnow(),
    )

    db.add(db_execution)
    await db.flush()

    # Return response
    return ExecutionResponse(
        execution_id=execution_id,
        script_content=execution.script_content,
        runtime=execution.runtime,
        args=execution.args,
        env_vars=execution.env_vars,
        status=ExecutionStatus.QUEUED,
        created_at=db_execution.created_at,
        started_at=None,
        completed_at=None,
        cost_micros=0,
    )


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ExecutionResponse:
    """Get execution status."""
    from sqlalchemy import select

    result = await db.execute(
        select(Execution).where(Execution.execution_id == execution_id)
    )
    db_execution = result.scalar_one_or_none()

    if not db_execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse(
        execution_id=db_execution.execution_id,
        script_content=db_execution.script_content,
        runtime=db_execution.runtime,
        args=db_execution.args,
        env_vars=db_execution.env_vars,
        status=ExecutionStatus(db_execution.status),
        exit_code=db_execution.exit_code,
        created_at=db_execution.created_at,
        started_at=db_execution.started_at,
        completed_at=db_execution.completed_at,
        cost_micros=db_execution.cost_micros,
    )
