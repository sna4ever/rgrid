"""Artifact database model (Story 7-2)."""

from datetime import datetime, timedelta
from sqlalchemy import String, BigInteger, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=30)
    )
