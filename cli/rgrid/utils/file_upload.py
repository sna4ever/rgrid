"""File upload utilities for MinIO."""

import httpx
from pathlib import Path


def upload_file_to_minio(file_path: str, presigned_url: str, timeout: int = 300) -> bool:
    """
    Upload a file to MinIO using a presigned PUT URL.

    Args:
        file_path: Local file path to upload
        presigned_url: Presigned PUT URL from MinIO
        timeout: Upload timeout in seconds (default 300 for large files)

    Returns:
        True if upload successful, False otherwise
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return False

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Upload using PUT request to presigned URL
        with httpx.Client(timeout=timeout) as client:
            response = client.put(presigned_url, content=file_content)
            return response.status_code == 200

    except Exception:
        return False
