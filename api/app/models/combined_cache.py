"""Combined cache database model (Story 6-3)."""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CombinedCache(Base):
    """Combined cache for complete execution environment (script + deps + runtime).

    Stores hashes of script content + requirements.txt + runtime to enable
    automatic cache invalidation when ANY input changes. This is critical
    for data integrity - cache invalidation bugs cause data corruption!
    """

    __tablename__ = "combined_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    combined_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    docker_image_tag: Mapped[str] = mapped_column(String(255), nullable=False)
    script_content: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_content: Mapped[str] = mapped_column(Text, nullable=False)
    runtime: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
