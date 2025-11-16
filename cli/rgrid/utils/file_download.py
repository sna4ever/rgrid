"""File download utilities (Story 7-5)."""

import httpx
from pathlib import Path
from typing import Any


def download_artifact_from_minio(s3_key: str, local_path: str, client: Any) -> bool:
    """
    Download an artifact from MinIO to local filesystem.

    Args:
        s3_key: S3 object key (e.g., "executions/exec_123/outputs/file.txt")
        local_path: Local filesystem path to save the file
        client: API client instance

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        # Get presigned download URL from API
        download_url = client.get_artifact_download_url(s3_key)

        if not download_url:
            return False

        # Download file using presigned URL
        response = httpx.get(download_url, timeout=300.0)
        response.raise_for_status()

        # Write to local file
        Path(local_path).write_bytes(response.content)

        return True

    except Exception as e:
        # Log error but don't raise to allow continuing with other files
        print(f"Download error for {s3_key}: {e}")
        return False
