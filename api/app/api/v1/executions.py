"""Execution endpoints."""

import logging
import secrets
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request
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
        user_metadata=execution.user_metadata,  # Story 10.8 - User metadata tags
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
        user_metadata=execution.user_metadata,  # Story 10.8
    )


@router.get("/executions")
async def list_executions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    limit: int = 50,
    status: str | None = None,
) -> list[Dict]:
    """
    List executions with optional filtering (Story 10.8).

    Args:
        request: FastAPI Request object for accessing query params
        db: Database session
        api_key: Authenticated API key
        limit: Maximum number of results (default 50)
        status: Optional status filter (queued, running, completed, failed)

    Query parameters for metadata filtering:
        metadata[key]=value - Filter by user_metadata field

    Returns:
        List of execution summaries
    """
    from sqlalchemy import select, desc

    # Parse metadata filters from query params (metadata[key]=value)
    metadata_filters = {}
    for key, value in request.query_params.items():
        if key.startswith("metadata[") and key.endswith("]"):
            # Extract the metadata key name
            meta_key = key[9:-1]  # Remove "metadata[" and "]"
            metadata_filters[meta_key] = value

    # Build query
    query = select(Execution)

    # Apply status filter if provided
    if status:
        query = query.where(Execution.status == status)

    # Apply metadata filters (Story 10.8)
    if metadata_filters:
        for meta_key, meta_value in metadata_filters.items():
            # Use JSON containment operator for filtering
            query = query.where(
                Execution.user_metadata.op("@>")(
                    {meta_key: meta_value}
                )
            )

    # Order by created_at descending (newest first)
    query = query.order_by(desc(Execution.created_at))

    # Apply limit
    query = query.limit(limit)

    result = await db.execute(query)
    executions = result.scalars().all()

    # Build response list
    execution_list = []
    for exec in executions:
        execution_list.append({
            "execution_id": exec.execution_id,
            "status": exec.status,
            "created_at": exec.created_at.isoformat() if exec.created_at else None,
            "started_at": exec.started_at.isoformat() if exec.started_at else None,
            "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
            "duration_seconds": exec.duration_seconds,
            "exit_code": exec.exit_code,
            "cost_micros": exec.cost_micros,
            "user_metadata": exec.user_metadata,
        })

    return execution_list


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
        # Auto-retry tracking (Story 10-7)
        retry_count=db_execution.retry_count,
        max_retries=db_execution.max_retries,
        # User metadata (Story 10.8)
        user_metadata=db_execution.user_metadata,
    )


@router.post("/executions/{execution_id}/retry", response_model=ExecutionResponse)
async def retry_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ExecutionResponse:
    """
    Retry an execution with the same parameters (Story 10-6).

    Creates a new execution using the script, runtime, args, env vars,
    and input files from the original execution.

    Args:
        execution_id: Original execution ID to retry
        db: Database session
        api_key: Authenticated API key

    Returns:
        New execution response with new execution_id
    """
    from sqlalchemy import select

    # 1. Fetch original execution
    result = await db.execute(
        select(Execution).where(Execution.execution_id == execution_id)
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Original execution not found")

    # 2. Generate new execution ID
    new_execution_id = f"exec_{secrets.token_hex(16)}"

    # 3. Copy input files in MinIO (if any)
    upload_urls: Dict[str, str] = {}
    download_urls: Dict[str, str] = {}

    if original.input_files:
        for filename in original.input_files:
            # Original object key
            old_key = f"executions/{execution_id}/inputs/{filename}"
            # New object key
            new_key = f"executions/{new_execution_id}/inputs/{filename}"

            # Copy file in MinIO
            try:
                minio_client.copy_object(old_key, new_key)
                logger.info(f"Copied input file {filename} to new execution {new_execution_id}")
            except Exception as e:
                logger.warning(f"Failed to copy input file {filename}: {e}")
                # Continue anyway - user can re-upload if needed

            # Generate presigned URLs for the new execution
            upload_url = minio_client.generate_presigned_upload_url(new_key, expiration=3600)
            upload_urls[filename] = upload_url
            download_url = minio_client.generate_presigned_download_url(new_key, expiration=7200)
            download_urls[filename] = download_url

    # 4. Create new execution record
    db_execution = Execution(
        execution_id=new_execution_id,
        script_content=original.script_content,
        runtime=original.runtime,
        args=original.args,
        env_vars=original.env_vars,
        input_files=original.input_files,
        batch_id=None,  # Retry is not part of original batch
        requirements_content=original.requirements_content,
        user_metadata=original.user_metadata,  # Story 10.8 - Preserve user metadata
        status=ExecutionStatus.QUEUED.value,
        created_at=datetime.utcnow(),
    )

    db.add(db_execution)

    # Submit Ray task if Ray is enabled
    ray_task_id: str | None = None
    if settings.ray_enabled and ray_service.is_initialized():
        ray_task_id = ray_service.submit_execution_task(
            execution_id=new_execution_id,
            database_url=settings.database_url
        )
        if ray_task_id:
            db_execution.ray_task_id = ray_task_id
            logger.info(f"Retry execution {new_execution_id} submitted to Ray (task: {ray_task_id})")

    await db.commit()

    logger.info(f"Created retry execution {new_execution_id} from {execution_id}")

    return ExecutionResponse(
        execution_id=new_execution_id,
        script_content=original.script_content,
        runtime=original.runtime,
        args=original.args,
        env_vars=original.env_vars,
        input_files=original.input_files,
        upload_urls=upload_urls if upload_urls else None,
        download_urls=download_urls if download_urls else None,
        status=ExecutionStatus.QUEUED,
        created_at=db_execution.created_at,
        started_at=None,
        completed_at=None,
        cost_micros=0,
        user_metadata=original.user_metadata,  # Story 10.8
    )


@router.get("/batches/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> Dict:
    """
    Get execution statuses for all jobs in a batch (Story 8-5).

    Args:
        batch_id: Batch ID to query
        db: Database session
        api_key: Authenticated API key

    Returns:
        Dictionary with list of execution statuses and total cost
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

    # Story 8-5: Calculate total cost for batch
    total_cost_micros = sum(exec.cost_micros or 0 for exec in executions)

    return {
        "statuses": statuses,
        "total_cost_micros": total_cost_micros,
    }


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
