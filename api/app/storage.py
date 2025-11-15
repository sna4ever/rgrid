"""
MinIO S3-compatible storage client.

Handles file uploads, downloads, and presigned URLs.
"""

from typing import Optional
from datetime import timedelta
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


class MinIOClient:
    """
    MinIO storage client.

    Wrapper around boto3 S3 client for MinIO operations.
    """

    def __init__(self) -> None:
        """Initialize MinIO client."""
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.minio_bucket_name

    async def init_bucket(self) -> None:
        """
        Initialize storage bucket.

        Creates the bucket if it doesn't exist.
        Should be called on application startup.
        """
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            # Bucket doesn't exist, create it
            self.client.create_bucket(Bucket=self.bucket_name)

    def generate_presigned_upload_url(
        self, object_key: str, expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for uploading a file.

        Args:
            object_key: S3 object key (file path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned upload URL
        """
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url

    def generate_presigned_download_url(
        self, object_key: str, expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for downloading a file.

        Args:
            object_key: S3 object key (file path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned download URL
        """
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url

    def upload_file(self, file_path: str, object_key: str) -> None:
        """
        Upload a file directly to MinIO.

        Args:
            file_path: Local file path
            object_key: S3 object key (destination path in bucket)
        """
        self.client.upload_file(file_path, self.bucket_name, object_key)

    def download_file(self, object_key: str, file_path: str) -> None:
        """
        Download a file from MinIO.

        Args:
            object_key: S3 object key (file path in bucket)
            file_path: Local destination file path
        """
        self.client.download_file(self.bucket_name, object_key, file_path)

    def delete_file(self, object_key: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_key: S3 object key (file path in bucket)
        """
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_key: S3 object key (file path in bucket)

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False


# Global MinIO client instance
minio_client = MinIOClient()
