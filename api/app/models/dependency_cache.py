"""Dependency cache database model (Story 6-2)."""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DependencyCache(Base):
    """Dependency layer cache for Docker BuildKit optimization.

    Stores hashes of requirements.txt files and their corresponding
    Docker layer IDs to avoid reinstalling the same dependencies.
    """

    __tablename__ = "dependency_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deps_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    docker_layer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    requirements_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
