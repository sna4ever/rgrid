"""Execution log database model (Story 8-3)."""

from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import String, BigInteger, DateTime, Integer, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def generate_log_id() -> str:
    """Generate unique log ID."""
    return f"log_{uuid.uuid4().hex[:16]}"


class ExecutionLog(Base):
    """
    Log entry for execution output.

    Stores stdout/stderr lines with sequence numbers for cursor-based
    streaming and reconnection support.
    """

    __tablename__ = "execution_logs"
    __table_args__ = (
        # Composite index for efficient cursor-based queries
        Index("idx_execution_logs_cursor", "execution_id", "sequence_number"),
        {'extend_existing': True}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    execution_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("executions.execution_id"), index=True
    )

    # Sequence number for ordering (monotonic counter per execution)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Log content
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    stream: Mapped[str] = mapped_column(String(16), nullable=False)  # "stdout" | "stderr"
    message: Mapped[str] = mapped_column(Text, nullable=False)

    def __init__(
        self,
        execution_id: str,
        sequence_number: int,
        stream: str,
        message: str,
        log_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        **kwargs
    ):
        """
        Initialize ExecutionLog entry.

        Args:
            execution_id: Parent execution ID
            sequence_number: Monotonic counter for this execution
            stream: "stdout" or "stderr"
            message: Log line content
            log_id: Unique log ID (auto-generated if not provided)
            timestamp: Log timestamp (defaults to now)
        """
        super().__init__(**kwargs)
        self.log_id = log_id or generate_log_id()
        self.execution_id = execution_id
        self.sequence_number = sequence_number
        self.stream = stream
        self.message = message
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_id": self.log_id,
            "execution_id": self.execution_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
            "stream": self.stream,
            "message": self.message,
        }
