"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables and .env file.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    All settings are loaded from environment variables.
    See .env.example for available configuration options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_debug: bool = Field(default=False, description="Enable debug mode")
    api_secret_key: str = Field(..., description="Secret key for JWT tokens")

    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql://user:pass@localhost:5432/rgrid"],
    )

    # MinIO Configuration
    minio_endpoint: str = Field(..., description="MinIO endpoint (host:port)")
    minio_access_key: str = Field(..., description="MinIO access key")
    minio_secret_key: str = Field(..., description="MinIO secret key")
    minio_bucket_name: str = Field(default="rgrid", description="MinIO bucket name")
    minio_use_ssl: bool = Field(default=False, description="Use SSL for MinIO")

    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:3000",
        description="Allowed CORS origins (comma-separated)",
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.api_debug


# Global settings instance
settings = Settings()  # type: ignore[call-arg]
