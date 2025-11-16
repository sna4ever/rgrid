#!/usr/bin/env python3
"""
Dead Worker Cleanup Daemon (Story NEW-7).

Continuously monitors for dead workers and marks their jobs as failed.

Usage:
    python runner/cleanup_daemon.py

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (required)
    STALE_THRESHOLD_MINUTES: Minutes without heartbeat to consider worker dead (default: 2)
    CHECK_INTERVAL: Seconds between cleanup checks (default: 60)
"""

import asyncio
import logging
import os
import signal
import sys

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner.runner.heartbeat import DeadWorkerCleaner


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CleanupDaemon:
    """Dead worker cleanup daemon runner."""

    def __init__(
        self,
        database_url: str,
        stale_threshold_minutes: int = 2,
        check_interval: float = 60.0,
    ):
        """
        Initialize cleanup daemon.

        Args:
            database_url: PostgreSQL connection string
            stale_threshold_minutes: Minutes without heartbeat to consider worker dead
            check_interval: Seconds between cleanup checks
        """
        self.database_url = database_url
        self.running = False

        # Create async engine
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create cleaner
        self.cleaner = DeadWorkerCleaner(
            stale_threshold_minutes=stale_threshold_minutes,
            check_interval=check_interval,
        )

    async def start(self):
        """Start the cleanup daemon."""
        logger.info("Starting Dead Worker Cleanup Daemon")
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # Start cleanup loop
            await self.cleaner.start_cleanup_loop(self.async_session_maker)
        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown daemon."""
        logger.info("Shutting down cleanup daemon...")
        self.running = False

        # Stop cleanup loop
        self.cleaner.stop_cleanup_loop()

        # Close database engine
        await self.engine.dispose()

        logger.info("Cleanup daemon shut down complete")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.cleaner.stop_cleanup_loop()


async def main():
    """Main entry point."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Ensure it uses asyncpg driver
    if "postgresql://" in database_url and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Get configuration from environment
    stale_threshold_minutes = int(os.getenv("STALE_THRESHOLD_MINUTES", "2"))
    check_interval = float(os.getenv("CHECK_INTERVAL", "60"))

    logger.info(f"Configuration:")
    logger.info(f"  Stale threshold: {stale_threshold_minutes} minutes")
    logger.info(f"  Check interval: {check_interval} seconds")

    # Create and start daemon
    daemon = CleanupDaemon(
        database_url=database_url,
        stale_threshold_minutes=stale_threshold_minutes,
        check_interval=check_interval,
    )

    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await daemon.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
