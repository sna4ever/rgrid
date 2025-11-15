"""
Pytest configuration and shared fixtures.
"""

import pytest
from typing import AsyncGenerator
import asyncio


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize test database tables."""
    try:
        from app.database import init_db, close_db

        await init_db()
        yield
        await close_db()
    except ImportError:
        # API not installed, skip
        yield
