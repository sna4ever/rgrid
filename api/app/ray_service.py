"""Ray service for distributed task execution (Tier 4 - Story 3-3)."""

import logging
from typing import Optional
from contextlib import asynccontextmanager

import ray
from ray import ObjectRef

from app.config import settings

logger = logging.getLogger(__name__)


class RayService:
    """Service for interacting with Ray cluster."""

    def __init__(self):
        """Initialize Ray service."""
        self._initialized = False
        self._ray_enabled = settings.ray_enabled
        self._ray_address = settings.ray_head_address

    def initialize(self) -> bool:
        """
        Initialize Ray client connection.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._ray_enabled:
            logger.info("Ray is disabled in configuration")
            return False

        if self._initialized:
            logger.debug("Ray already initialized")
            return True

        try:
            # Initialize Ray client
            ray.init(
                address=self._ray_address,
                ignore_reinit_error=True,
                namespace="rgrid",
                logging_level=logging.INFO,
            )
            self._initialized = True
            logger.info(f"Ray client initialized successfully to {self._ray_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Ray client: {e}", exc_info=True)
            self._initialized = False
            return False

    def shutdown(self):
        """Shutdown Ray client connection."""
        if self._initialized:
            try:
                ray.shutdown()
                self._initialized = False
                logger.info("Ray client shutdown successfully")
            except Exception as e:
                logger.error(f"Error shutting down Ray client: {e}")

    def is_initialized(self) -> bool:
        """Check if Ray is initialized."""
        return self._initialized

    def submit_execution_task(
        self,
        execution_id: str,
        database_url: str
    ) -> Optional[str]:
        """
        Submit an execution task to Ray cluster.

        Args:
            execution_id: Execution ID to process
            database_url: Database connection string

        Returns:
            Ray task ID (hex string) if successful, None otherwise
        """
        if not self._initialized:
            logger.warning("Ray not initialized, cannot submit task")
            return None

        try:
            # Import the remote task function
            # Note: This must be done after ray.init()
            from runner.ray_tasks import execute_script_task

            # Submit task to Ray
            task_ref: ObjectRef = execute_script_task.remote(execution_id, database_url)

            # Get task ID as hex string for storage
            task_id = task_ref.hex()

            logger.info(f"Submitted Ray task {task_id} for execution {execution_id}")
            return task_id

        except Exception as e:
            logger.error(
                f"Failed to submit Ray task for execution {execution_id}: {e}",
                exc_info=True
            )
            return None


# Global Ray service instance
ray_service = RayService()


@asynccontextmanager
async def lifespan_ray_service():
    """
    Lifespan context manager for Ray service.

    This should be called during FastAPI app startup/shutdown.
    """
    # Startup
    logger.info("Initializing Ray service...")
    ray_service.initialize()

    yield

    # Shutdown
    logger.info("Shutting down Ray service...")
    ray_service.shutdown()
