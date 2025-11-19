"""
Pytest configuration and shared fixtures.
"""

import pytest
from typing import AsyncGenerator
import asyncio
import sys
from pathlib import Path

# Add api and cli to Python path for imports (Story 10-4)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "api"))
sys.path.insert(0, str(project_root / "cli"))


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


@pytest.fixture(scope="session")
async def init_test_db():
    """Initialize test database tables.

    Note: Not autouse to avoid async fixture issues with sync tests.
    Tests that need this should explicitly request it.
    """
    try:
        from app.database import init_db, close_db

        await init_db()
        yield
        await close_db()
    except ImportError:
        # API not installed, skip
        yield
