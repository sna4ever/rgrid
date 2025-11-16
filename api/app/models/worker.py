"""Worker database models."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class Worker(Base):
    """Worker node record."""

    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # Hetzner server ID
    ray_node_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # Ray internal node ID
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4/IPv6 address
    max_concurrent: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(32), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    terminated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WorkerHeartbeat(Base):
    """Worker heartbeat tracking."""

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ray_available_resources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
