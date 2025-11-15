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

    pass


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

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Cost tracking
    cost_micros: int = Field(default=0, ge=0, description="Cost in micros")


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
