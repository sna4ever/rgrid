"""
RGrid API - FastAPI Application.

Main application entrypoint with middleware, CORS, and route configuration.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.storage import minio_client
from app.api.v1.health import router as health_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting RGrid API...")

    # Initialize database
    logger.info("Initializing database connection pool...")
    await init_db()
    logger.info("Database initialized")

    # Initialize MinIO
    logger.info("Initializing MinIO client...")
    await minio_client.init_bucket()
    logger.info(f"MinIO initialized (bucket: {settings.minio_bucket_name})")

    logger.info("RGrid API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down RGrid API...")
    await close_db()
    logger.info("RGrid API shut down")


# Create FastAPI application
app = FastAPI(
    title="RGrid API",
    description="Remote Python Script Execution Platform",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])

from app.api.v1.executions import router as executions_router

app.include_router(executions_router, prefix="/api/v1", tags=["executions"])


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": "RGrid API",
        "version": "0.1.0",
        "docs": "/docs" if settings.is_development else "disabled",
    }
