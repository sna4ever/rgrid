"""Execution endpoints."""

import logging
import secrets
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.v1.auth import verify_api_key
from app.models.execution import Execution
from app.storage import minio_client
from app.ray_service import ray_service
from app.config import settings
from rgrid_common.models import ExecutionCreate, ExecutionResponse
from rgrid_common.types import ExecutionStatus

logger = logging.getLogger(__name__)
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
        Created execution with presigned upload URLs for input files
    """
    # Generate execution ID
    execution_id = f"exec_{secrets.token_hex(16)}"

    # Generate presigned upload URLs for input files (Tier 4 - Story 2-5)
    upload_urls: Dict[str, str] = {}
    download_urls: Dict[str, str] = {}

    for filename in execution.input_files:
        # Object key: executions/{exec_id}/inputs/{filename}
        object_key = f"executions/{execution_id}/inputs/{filename}"

        # Generate presigned PUT URL for CLI to upload file
        upload_url = minio_client.generate_presigned_upload_url(object_key, expiration=3600)
        upload_urls[filename] = upload_url

        # Also generate presigned GET URL for runner to download file
        download_url = minio_client.generate_presigned_download_url(object_key, expiration=7200)
        download_urls[filename] = download_url

    # Create database record
    runtime_str = execution.runtime.value if hasattr(execution.runtime, 'value') else execution.runtime
    db_execution = Execution(
        execution_id=execution_id,
        script_content=execution.script_content,
        runtime=runtime_str,
        args=execution.args,
        env_vars=execution.env_vars,
        input_files=execution.input_files,  # Tier 4 - Story 2-5
        batch_id=execution.batch_id,  # Tier 5 - Story 5-3
        requirements_content=execution.requirements_content,  # Story 2.4 - Python deps
        status=ExecutionStatus.QUEUED.value,
        created_at=datetime.utcnow(),
    )

    db.add(db_execution)
    await db.flush()

    # Submit Ray task if Ray is enabled and initialized (Tier 4 - Story 3-3)
    ray_task_id: str | None = None
    if settings.ray_enabled and ray_service.is_initialized():
        ray_task_id = ray_service.submit_execution_task(
            execution_id=execution_id,
            database_url=settings.database_url
        )

        if ray_task_id:
            # Update execution record with Ray task ID
            db_execution.ray_task_id = ray_task_id
            logger.info(f"Execution {execution_id} submitted to Ray (task: {ray_task_id})")
        else:
            logger.warning(f"Failed to submit execution {execution_id} to Ray - will use polling worker")

    await db.commit()

    # Return response with presigned URLs
    return ExecutionResponse(
        execution_id=execution_id,
        script_content=execution.script_content,
        runtime=execution.runtime,
        args=execution.args,
        env_vars=execution.env_vars,
        input_files=execution.input_files,
        upload_urls=upload_urls if upload_urls else None,
        download_urls=download_urls if download_urls else None,
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
        stdout=db_execution.stdout,
        stderr=db_execution.stderr,
        output_truncated=db_execution.output_truncated,
        execution_error=db_execution.execution_error,
        created_at=db_execution.created_at,
        started_at=db_execution.started_at,
        completed_at=db_execution.completed_at,
        cost_micros=db_execution.cost_micros,
    )


@router.get("/batches/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> Dict:
    """
    Get execution statuses for all jobs in a batch.

    Args:
        batch_id: Batch ID to query
        db: Database session
        api_key: Authenticated API key

    Returns:
        Dictionary with list of execution statuses
    """
    from sqlalchemy import select

    # Query all executions with this batch_id
    result = await db.execute(
        select(Execution).where(Execution.batch_id == batch_id)
    )
    executions = result.scalars().all()

    if not executions:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Extract statuses
    statuses = [exec.status for exec in executions]

    return {"statuses": statuses}


@router.get("/batches/{batch_id}/executions")
async def get_batch_executions(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> list[Dict]:
    """
    Get all executions in a batch with full metadata (Story 5-4).

    Args:
        batch_id: Batch ID to query
        db: Database session
        api_key: Authenticated API key

    Returns:
        List of execution dictionaries with metadata including input_files
    """
    from sqlalchemy import select

    # Query all executions with this batch_id
    result = await db.execute(
        select(Execution).where(Execution.batch_id == batch_id)
    )
    executions = result.scalars().all()

    if not executions:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Build execution list with batch metadata
    execution_list = []
    for exec in executions:
        # Extract input filename from args or input_files
        input_file = None
        if exec.input_files:
            # Get first input file if available
            input_file = exec.input_files[0] if isinstance(exec.input_files, list) and exec.input_files else None
        elif exec.args:
            # Fallback: look for filename in args
            for arg in exec.args:
                if isinstance(arg, str) and '.' in arg:
                    input_file = arg
                    break

        execution_list.append({
            "execution_id": exec.execution_id,
            "status": exec.status,
            "batch_metadata": {
                "input_file": input_file,
            },
            "created_at": exec.created_at.isoformat() if exec.created_at else None,
            "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
        })

    return execution_list


@router.get("/executions/{execution_id}/artifacts")
async def get_execution_artifacts(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> list[Dict]:
    """
    Get list of artifacts for an execution (Story 7-5).

    Args:
        execution_id: Execution ID to query
        db: Database session
        api_key: Authenticated API key

    Returns:
        List of artifact metadata dictionaries
    """
    from sqlalchemy import select
    from app.models.artifact import Artifact

    # Query all artifacts for this execution
    result = await db.execute(
        select(Artifact).where(Artifact.execution_id == execution_id)
    )
    artifacts = result.scalars().all()

    # Convert to dictionaries
    artifact_list = []
    for artifact in artifacts:
        artifact_list.append({
            "artifact_id": artifact.artifact_id,
            "execution_id": artifact.execution_id,
            "artifact_type": artifact.artifact_type,
            "filename": artifact.filename,
            "file_path": artifact.file_path,
            "size_bytes": artifact.size_bytes,
            "content_type": artifact.content_type,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None,
        })

    return artifact_list


@router.post("/artifacts/download-url")
async def get_artifact_download_url(
    request: Dict,
    api_key: str = Depends(verify_api_key),
) -> Dict[str, str]:
    """
    Get presigned download URL for an artifact (Story 7-5).

    Args:
        request: Dictionary with "s3_key" field
        api_key: Authenticated API key

    Returns:
        Dictionary with "download_url" field
    """
    s3_key = request.get("s3_key")
    if not s3_key:
        raise HTTPException(status_code=400, detail="Missing s3_key in request")

    # Generate presigned GET URL (2 hour expiration)
    download_url = minio_client.generate_presigned_download_url(s3_key, expiration=7200)

    return {"download_url": download_url}
