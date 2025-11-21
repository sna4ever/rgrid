"""
Database connection and session management.

Uses SQLAlchemy 2.0 async engine with asyncpg driver.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Create async engine
# Note: Use NullPool for development to avoid connection issues
engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    future=True,
    poolclass=NullPool if settings.is_development else None,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database.

    Creates all tables defined in Base.metadata.
    Should be called on application startup.
    """
    # Import models to register them with Base.metadata
    from app.models.execution import Execution  # noqa: F401
    from app.models.execution_log import ExecutionLog  # noqa: F401
    from app.models.api_key import APIKey  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.

    Should be called on application shutdown.
    """
    await engine.dispose()
