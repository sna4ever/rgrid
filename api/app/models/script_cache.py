"""Script cache database model (Story 6-1).

Caches Docker images by script content hash to enable instant
execution for repeated identical scripts.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScriptCache(Base):
    """Script content cache for Docker image reuse (Story 6-1).

    Stores SHA256 hashes of script content mapped to Docker image IDs.
    When a script is submitted, the hash is computed and checked against
    this table. If a match is found (cache hit), the cached Docker image
    is used instead of rebuilding.

    The cache key is (script_hash, runtime) because the same script
    with different runtimes produces different Docker images.

    Attributes:
        id: Auto-incrementing primary key
        script_hash: SHA256 hash of script content (64 hex chars)
        runtime: Docker runtime image (e.g., "python:3.11")
        docker_image_id: Cached Docker image ID (e.g., "sha256:abc...")
        created_at: When this cache entry was created
    """

    __tablename__ = "script_cache"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime: Mapped[str] = mapped_column(String(128), nullable=False)
    docker_image_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
