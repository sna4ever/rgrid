"""File handling utilities for runner."""

import httpx
from pathlib import Path
from typing import Dict, List


def download_input_files(download_urls: Dict[str, str], work_dir: Path) -> Dict[str, Path]:
    """
    Download input files from MinIO to work directory.

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
            # Download file from presigned URL
            with httpx.Client(timeout=300) as client:
                response = client.get(url)
                if response.status_code == 200:
                    # Write to work directory
                    file_path = work_dir / filename
                    file_path.write_bytes(response.content)
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
