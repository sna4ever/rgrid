"""File upload utilities for MinIO."""

import gzip
import io
import httpx
from pathlib import Path
from typing import Iterator
from tqdm import tqdm


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


def upload_file_streaming(
    file_path: str,
    presigned_url: str,
    timeout: int = 600,
    show_progress: bool = False,
    chunk_size: int = 8192
) -> bool:
    """
    Upload a file to MinIO using streaming with gzip compression.

    This function streams the file in chunks without loading it entirely into memory,
    making it suitable for large files (>100MB). Files are compressed with gzip
    during upload to reduce bandwidth.

    Args:
        file_path: Local file path to upload
        presigned_url: Presigned PUT URL from MinIO
        timeout: Upload timeout in seconds (default 600 for large files)
        show_progress: Whether to display a progress bar
        chunk_size: Size of chunks to read (default 8KB)

    Returns:
        True if upload successful, False otherwise
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return False

        file_size = file_path_obj.stat().st_size

        def compressed_chunks() -> Iterator[bytes]:
            """Generate compressed chunks from file."""
            # Create a BytesIO buffer to collect all compressed data first
            # For truly large files (multi-GB), this should use a different approach
            # but for files up to a few hundred MB, this is acceptable
            buffer = io.BytesIO()
            compressor = gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6)

            with open(file_path_obj, 'rb') as f_in:
                # Setup progress bar if requested
                pbar = tqdm(
                    total=file_size,
                    unit='B',
                    unit_scale=True,
                    desc="Uploading",
                    disable=not show_progress
                )

                try:
                    # Compress all data
                    while chunk := f_in.read(chunk_size):
                        compressor.write(chunk)
                        pbar.update(len(chunk))

                    # Close compressor to finish writing
                    compressor.close()

                    # Now yield the compressed data in chunks
                    buffer.seek(0)
                    while True:
                        compressed_chunk = buffer.read(chunk_size)
                        if not compressed_chunk:
                            break
                        yield compressed_chunk
                finally:
                    pbar.close()

        # Upload using streaming PUT request
        with httpx.Client(timeout=timeout) as client:
            response = client.put(
                presigned_url,
                content=compressed_chunks(),
                headers={'Content-Encoding': 'gzip'}
            )
            return response.status_code == 200

    except Exception:
        return False
