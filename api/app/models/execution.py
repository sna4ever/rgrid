"""Execution database model."""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, BigInteger, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class Execution(Base):
    """Execution record."""

    __tablename__ = "executions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    script_content: Mapped[str] = mapped_column(Text)
    runtime: Mapped[str] = mapped_column(String(50))
    args: Mapped[dict] = mapped_column(JSON, default=list)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    input_files: Mapped[dict] = mapped_column(JSON, default=list)  # Tier 4 - Story 2-5
    status: Mapped[str] = mapped_column(String(50), index=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Output fields (Tier 2)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Cost tracking (Epic 9)
    cost_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    finalized_cost_micros: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    cost_finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Ray/worker tracking (Tier 4 - Story 3-3)
    ray_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Batch tracking (Tier 5 - Story 5-3)
    batch_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Python dependency management (Story 2.4)
    requirements_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution metadata tracking (Story 8.6)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    worker_hostname: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    execution_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
