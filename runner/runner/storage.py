"""MinIO storage client for runner."""

import os
import boto3
from botocore.config import Config
from typing import Optional


class MinIOClient:
    """Minimal MinIO client for runner to generate download URLs."""

    def __init__(self):
        """Initialize MinIO client from environment variables."""
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "rgrid_dev")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "rgrid_dev_secret")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "rgrid")
        self.use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

        self.client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if self.use_ssl else ''}://{self.endpoint}",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
        )

    def generate_presigned_download_url(
        self, object_key: str, expiration: int = 3600
    ) -> str:
        """
        Generate presigned download URL for an object.

        Args:
            object_key: S3 object key (e.g., "executions/exec_123/inputs/file.json")
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned GET URL
        """
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url


# Global instance
minio_client = MinIOClient()
