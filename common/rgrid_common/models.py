"""
Shared Pydantic models for RGrid.

These models are used for data validation and serialization across components.
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from rgrid_common.types import ExecutionStatus, RuntimeType, FileType


class ExecutionBase(BaseModel):
    """Base model for execution data."""

    model_config = ConfigDict(use_enum_values=True)

    script_content: str = Field(..., description="Python script source code")
    runtime: RuntimeType = Field(
        default=RuntimeType.PYTHON_311, description="Runtime environment"
    )
    args: List[str] = Field(default_factory=list, description="Script command-line arguments")
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Execution timeout")


class ExecutionCreate(ExecutionBase):
    """Model for creating a new execution."""

    input_files: List[str] = Field(
        default_factory=list,
        description="List of input file names to be uploaded to MinIO"
    )
    batch_id: Optional[str] = Field(
        None,
        description="Optional batch ID for grouping multiple executions (Tier 5 - Story 5-3)"
    )
    requirements_content: Optional[str] = Field(
        None,
        description="Optional requirements.txt content for auto-installing Python dependencies (Story 2.4)"
    )
    user_metadata: Optional[Dict[str, str]] = Field(
        None,
        description="User-provided metadata tags for organizing executions (Story 10.8)"
    )


class ExecutionResponse(ExecutionBase):
    """Model for execution response."""

    execution_id: str = Field(..., description="Unique execution ID")
    status: ExecutionStatus = Field(..., description="Current execution status")
    exit_code: Optional[int] = Field(None, description="Process exit code")

    # Output fields (Tier 2)
    stdout: Optional[str] = Field(None, description="Standard output from execution")
    stderr: Optional[str] = Field(None, description="Standard error from execution")
    output_truncated: bool = Field(default=False, description="Whether output was truncated")
    execution_error: Optional[str] = Field(None, description="Error message if execution failed")

    # File handling (Tier 4 - Story 2-5)
    input_files: List[str] = Field(
        default_factory=list,
        description="List of input file names"
    )
    upload_urls: Optional[Dict[str, str]] = Field(
        None,
        description="Presigned URLs for uploading input files (filename -> URL)"
    )
    download_urls: Optional[Dict[str, str]] = Field(
        None,
        description="Presigned URLs for downloading input files (filename -> URL)"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Cost tracking (Epic 9)
    cost_micros: int = Field(default=0, ge=0, description="Estimated cost in micros (1 EUR = 1,000,000 micros)")
    finalized_cost_micros: Optional[int] = Field(None, ge=0, description="Finalized cost after billing hour amortization")
    cost_finalized_at: Optional[datetime] = Field(None, description="When cost was finalized")

    # Execution metadata tracking (Story 8.6)
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds")
    worker_hostname: Optional[str] = Field(None, description="Worker node hostname")
    execution_metadata: Optional[Dict[str, str]] = Field(
        None, description="Extensible execution metadata (runtime_version, python_version, etc.)"
    )

    # Auto-retry tracking (Story 10-7)
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts made")
    max_retries: int = Field(default=2, ge=0, description="Maximum retries allowed")

    # User metadata (Story 10.8)
    user_metadata: Optional[Dict[str, str]] = Field(
        None, description="User-provided metadata tags (project, env, etc.)"
    )


class FileMetadata(BaseModel):
    """Metadata for a file in the system."""

    model_config = ConfigDict(use_enum_values=True)

    file_key: str = Field(..., description="S3 object key")
    file_type: FileType = Field(..., description="Type of file")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    content_hash: str = Field(..., description="SHA256 hash of content")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: datetime = Field(..., description="Log timestamp")
    stream: str = Field(..., description="Stream (stdout/stderr)")
    message: str = Field(..., description="Log message")


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Response timestamp")
