"""Execution database model."""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class Execution(Base):
    """Execution record."""

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    script_content: Mapped[str] = mapped_column(Text)
    runtime: Mapped[str] = mapped_column(String(50))
    args: Mapped[dict] = mapped_column(JSON, default=list)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), index=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cost_micros: Mapped[int] = mapped_column(BigInteger, default=0)
