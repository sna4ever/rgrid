"""Input cache database model (Story 6-4).

Caches input file references by combined hash to enable skipping
re-uploads of identical input files across executions.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InputCache(Base):
    """Input file cache for MinIO reference reuse (Story 6-4).

    Stores combined SHA256 hashes of input files mapped to their MinIO
    object keys. When the same input files are used again, the hash
    is computed and checked against this table. If a match is found
    (cache hit), the CLI skips uploading and uses the cached file
    references.

    The cache entry stores:
    - input_hash: Combined SHA256 hash of all input file contents
    - file_references: JSON dict mapping filenames to MinIO object keys

    Attributes:
        id: Auto-incrementing primary key
        input_hash: Combined SHA256 hash of all input files (64 hex chars)
        file_references: JSON dict of {filename: minio_object_key}
        created_at: When this cache entry was created
        last_used_at: When this cache entry was last used (for TTL)
        use_count: Number of cache hits (for analytics)
    """

    __tablename__ = "input_cache"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_references: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
