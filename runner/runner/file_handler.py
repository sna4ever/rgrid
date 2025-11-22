"""File handling utilities for runner.

SECURITY: This module handles untrusted filenames from API responses.
All filenames MUST be validated to prevent path traversal attacks.
"""

import gzip
import httpx
from pathlib import Path
from typing import Dict, List


class PathTraversalError(ValueError):
    """Raised when a path traversal attack is detected."""
    pass


def validate_safe_filename(filename: str, base_dir: Path) -> Path:
    """
    Validate that a filename is safe and resolves within base_dir.

    SECURITY: Prevents path traversal attacks by ensuring the resolved
    path stays within the intended directory.

    Args:
        filename: Untrusted filename from external source
        base_dir: Directory that the file must stay within

    Returns:
        Safe absolute path within base_dir

    Raises:
        PathTraversalError: If path traversal is detected
    """
    # Check for obvious path traversal patterns
    if '..' in filename:
        raise PathTraversalError(f"Path traversal detected in filename: '{filename}'")

    if filename.startswith('/'):
        raise PathTraversalError(f"Absolute path not allowed: '{filename}'")

    if '\x00' in filename:
        raise PathTraversalError(f"Null byte detected in filename: '{filename}'")

    # Resolve paths to check for traversal via symlinks or other tricks
    base_resolved = base_dir.resolve()
    target_path = base_dir / filename
    target_resolved = target_path.resolve()

    # Ensure target is within base directory
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path '{filename}' escapes base directory '{base_dir}'"
        )

    return target_path


def download_input_files(download_urls: Dict[str, str], work_dir: Path) -> Dict[str, Path]:
    """
    Download input files from MinIO to work directory using streaming.

    Files are downloaded with streaming to support large files (>100MB).
    Automatically decompresses gzip-compressed files.

    SECURITY: Validates all filenames to prevent path traversal attacks.

    Args:
        download_urls: Dict mapping filename to presigned download URL
        work_dir: Directory to download files into

    Returns:
        Dict mapping filename to downloaded file path
    """
    downloaded_files = {}

    # Ensure work directory exists
    work_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in download_urls.items():
        try:
            # SECURITY: Validate filename before use
            file_path = validate_safe_filename(filename, work_dir)

            # Download file with streaming from presigned URL
            with httpx.stream("GET", url, timeout=600) as response:
                if response.status_code == 200:
                    # Check if response is gzip compressed
                    content_encoding = response.headers.get('content-encoding', '')
                    is_gzipped = content_encoding.lower() == 'gzip'

                    with open(file_path, 'wb') as f_out:
                        if is_gzipped:
                            # Decompress on the fly
                            decompressor = gzip.GzipFile(fileobj=response.raw)
                            while True:
                                chunk = decompressor.read(8192)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                        else:
                            # Stream without decompression
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f_out.write(chunk)

                    downloaded_files[filename] = file_path
        except Exception:
            # Skip failed downloads (could add logging here)
            continue

    return downloaded_files


def map_args_to_container_paths(args: List[str], input_files: List[str]) -> List[str]:
    """
    Map file arguments to container paths (/work/filename).

    Replaces any argument that matches an input filename with /work/{filename}.

    Args:
        args: Original arguments
        input_files: List of input file names

    Returns:
        Arguments with file paths replaced by /work paths
    """
    container_args = []

    # Create a set of filenames for faster lookup
    input_file_set = set(input_files)

    for arg in args:
        # Extract filename from path if it's a path
        filename = Path(arg).name if '/' in arg or '\\' in arg else arg

        # If this argument matches an input file, replace with /work path
        if filename in input_file_set:
            container_args.append(f"/work/{filename}")
        else:
            container_args.append(arg)

    return container_args
