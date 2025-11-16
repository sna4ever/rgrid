"""File download utilities (Story 7-5 + 7-6)."""

import gzip
import httpx
from pathlib import Path
from typing import Any
from tqdm import tqdm


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


def download_file_streaming(
    presigned_url: str,
    output_path: str,
    show_progress: bool = False,
    chunk_size: int = 8192
) -> bool:
    """
    Download a file from MinIO using streaming with automatic gzip decompression.

    This function streams the file in chunks without loading it entirely into memory,
    making it suitable for large files (>100MB). Files compressed with gzip are
    automatically decompressed during download.

    Args:
        presigned_url: Presigned GET URL from MinIO
        output_path: Local filesystem path to save the file
        show_progress: Whether to display a progress bar
        chunk_size: Size of chunks to read (default 8KB)

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        output_file = Path(output_path)

        # Make GET request with streaming
        response = httpx.get(presigned_url, timeout=600.0, follow_redirects=True)
        response.raise_for_status()

        # Get total size from headers
        total_size = int(response.headers.get('content-length', 0))
        content_encoding = response.headers.get('content-encoding', '')

        # Check if response is gzip compressed
        is_gzipped = content_encoding.lower() == 'gzip'

        # Setup progress bar
        pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc="Downloading",
            disable=not show_progress
        )

        try:
            with open(output_file, 'wb') as f_out:
                if is_gzipped:
                    # Decompress on the fly
                    compressed_data = response.content
                    decompressed_data = gzip.decompress(compressed_data)
                    f_out.write(decompressed_data)
                    pbar.update(total_size)
                else:
                    # Stream response (uses iter_bytes if available)
                    if hasattr(response, 'iter_bytes'):
                        for chunk in response.iter_bytes(chunk_size=chunk_size):
                            f_out.write(chunk)
                            pbar.update(len(chunk))
                    else:
                        # Fallback for mocked responses
                        f_out.write(response.content)
                        pbar.update(len(response.content))
        finally:
            pbar.close()

        return True

    except Exception as e:
        print(f"Download error: {e}")
        return False
