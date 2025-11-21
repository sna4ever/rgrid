"""Auto-download functionality for execution outputs (Story 7-4).

This module provides functions to:
- Wait for execution completion
- Download output artifacts automatically
- Handle filename conflicts
- Display progress information
"""

import time
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from rgrid.utils.file_download import download_artifact_from_minio

console = Console()


def format_size(size_bytes: int) -> str:
    """
    Format bytes to human-readable size.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def resolve_filename_conflict(dest_dir: Path, filename: str, exec_id: str) -> Path:
    """
    Resolve filename conflicts by prefixing with execution ID.

    Args:
        dest_dir: Destination directory
        filename: Original filename
        exec_id: Execution ID for uniqueness

    Returns:
        Resolved path that doesn't conflict with existing files
    """
    dest_path = dest_dir / filename

    if not dest_path.exists():
        return dest_path

    # Prefix with first 8 chars of exec_id
    prefix = exec_id[:8]
    prefixed_name = f"{prefix}_{filename}"
    prefixed_path = dest_dir / prefixed_name

    if not prefixed_path.exists():
        return prefixed_path

    # If still conflicts, add counter
    counter = 2
    stem = Path(prefixed_name).stem
    suffix = Path(prefixed_name).suffix

    while True:
        numbered_name = f"{stem}_{counter}{suffix}"
        numbered_path = dest_dir / numbered_name
        if not numbered_path.exists():
            return numbered_path
        counter += 1


def wait_for_completion(
    client: Any,
    exec_id: str,
    timeout: int = 300,
    poll_interval: float = 2.0
) -> dict[str, Any]:
    """
    Poll until execution completes or times out.

    Args:
        client: API client instance
        exec_id: Execution ID to monitor
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        Final execution status dictionary

    Raises:
        TimeoutError: If execution doesn't complete within timeout
    """
    start = time.time()

    while time.time() - start < timeout:
        status = client.get_execution(exec_id)

        if status.get('status') in ('completed', 'failed'):
            return status

        time.sleep(poll_interval)

    raise TimeoutError(f"Execution {exec_id} did not complete within {timeout}s")


def download_outputs(
    client: Any,
    exec_id: str,
    dest_dir: Optional[Path] = None,
    show_progress: bool = True
) -> dict[str, int]:
    """
    Download all output artifacts from an execution.

    Args:
        client: API client instance
        exec_id: Execution ID
        dest_dir: Destination directory (defaults to current working directory)
        show_progress: Whether to display progress messages

    Returns:
        Dictionary with 'downloaded' and 'failed' counts
    """
    dest_dir = dest_dir or Path.cwd()

    # Get list of artifacts
    artifacts = client.get_artifacts(exec_id)

    # Filter to only output artifacts
    output_artifacts = [a for a in artifacts if a.get('artifact_type') == 'output']

    if not output_artifacts:
        if show_progress:
            console.print("[dim]No output files to download[/dim]")
        return {'downloaded': 0, 'failed': 0}

    if show_progress:
        console.print("\n[cyan]Downloading outputs:[/cyan]")

    downloaded = 0
    failed = 0

    for artifact in output_artifacts:
        filename = artifact.get('filename', 'unknown')
        size_bytes = artifact.get('size_bytes', 0)
        file_path = artifact.get('file_path')

        if not file_path:
            if show_progress:
                console.print(f"[yellow]![/yellow] No file path for {filename}")
            failed += 1
            continue

        # Resolve filename conflicts
        local_path = resolve_filename_conflict(dest_dir, filename, exec_id)

        # Download from MinIO
        success = download_artifact_from_minio(file_path, str(local_path), client)

        if success:
            downloaded += 1
            if show_progress:
                size_str = format_size(size_bytes)
                console.print(f"[green]✓[/green] {filename} ({size_str})")
        else:
            failed += 1
            if show_progress:
                console.print(f"[red]✗[/red] Failed to download: {filename}")

    if show_progress:
        console.print(f"\n[green]✓[/green] {downloaded} files downloaded to {dest_dir}")

    return {'downloaded': downloaded, 'failed': failed}
