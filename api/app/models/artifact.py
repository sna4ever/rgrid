"""Artifact database model (Story 7-2)."""

import os
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import String, BigInteger, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def get_retention_days() -> int:
    """Get artifact retention days from environment or config."""
    try:
        from app.config import settings
        return settings.artifact_retention_days
    except Exception:
        # Fallback to env var or default
        return int(os.getenv("ARTIFACT_RETENTION_DAYS", "30"))


class Artifact(Base):
    """Artifact record for uploaded/downloaded files."""

    __tablename__ = "artifacts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    execution_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("executions.execution_id"), index=True
    )

    # File metadata
    artifact_type: Mapped[str] = mapped_column(String(20))  # "input" | "output"
    filename: Mapped[str] = mapped_column(String(512))  # Original filename (with subdir)
    file_path: Mapped[str] = mapped_column(String(1024))  # MinIO object key
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(128))

    # Compression metadata (Story 7-6)
    compressed: Mapped[bool] = mapped_column(Boolean, default=False)
    original_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=True)

    # Retention (Story 7-3)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __init__(
        self,
        artifact_id: str,
        execution_id: str,
        artifact_type: str,
        filename: str,
        file_path: str,
        size_bytes: int,
        content_type: str,
        compressed: bool = False,
        original_size_bytes: Optional[int] = None,
        checksum_sha256: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        **kwargs
    ):
        """
        Initialize Artifact with automatic expiry calculation.

        Args:
            artifact_id: Unique artifact identifier
            execution_id: Parent execution ID
            artifact_type: Type of artifact ("input" or "output")
            filename: Original filename
            file_path: MinIO object key
            size_bytes: File size in bytes
            content_type: MIME content type
            compressed: Whether file is compressed
            original_size_bytes: Original size before compression
            checksum_sha256: SHA256 checksum
            created_at: Creation timestamp (defaults to now)
            expires_at: Expiry timestamp (defaults to created_at + retention_days)
        """
        super().__init__(**kwargs)
        self.artifact_id = artifact_id
        self.execution_id = execution_id
        self.artifact_type = artifact_type
        self.filename = filename
        self.file_path = file_path
        self.size_bytes = size_bytes
        self.content_type = content_type
        self.compressed = compressed
        self.original_size_bytes = original_size_bytes
        self.checksum_sha256 = checksum_sha256

        # Set timestamps with defaults
        self.created_at = created_at or datetime.utcnow()
        if expires_at is not None:
            self.expires_at = expires_at
        else:
            retention_days = get_retention_days()
            self.expires_at = self.created_at + timedelta(days=retention_days)
