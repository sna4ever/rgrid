"""Batch execution utilities for glob pattern expansion and submission.

Story 5-1: Implement --batch flag with glob pattern expansion.
"""

import glob
import secrets
from pathlib import Path
from typing import Any

from rgrid.utils.file_upload import upload_file_to_minio


def expand_glob_pattern(pattern: str) -> list[str]:
    """Expand a glob pattern to a list of matching file paths.

    Args:
        pattern: Glob pattern (e.g., "data/*.csv")

    Returns:
        Sorted list of matching file paths.

    Raises:
        ValueError: If no files match the pattern.
    """
    files = glob.glob(pattern)

    if not files:
        raise ValueError(f"No files match pattern '{pattern}'")

    # Return sorted for deterministic order
    return sorted(files)


def generate_batch_id() -> str:
    """Generate a unique batch ID with 'batch_' prefix.

    Returns:
        Unique batch ID string (e.g., "batch_a1b2c3d4e5f6")
    """
    return f"batch_{secrets.token_hex(8)}"


class BatchSubmitter:
    """Submit batch executions for multiple files."""

    def __init__(self, client: Any):
        """Initialize with API client.

        Args:
            client: RGrid API client instance.
        """
        self.client = client

    def submit_batch(
        self,
        script_content: str,
        files: list[str],
        runtime: str,
        env_vars: dict[str, str],
        args: list[str] | None = None,
        requirements_content: str | None = None,
    ) -> dict[str, Any]:
        """Submit batch executions, one per file.

        Args:
            script_content: Python script content to execute.
            files: List of file paths to process.
            runtime: Docker runtime image.
            env_vars: Environment variables dict.
            args: Additional arguments to pass to script.
            requirements_content: Optional requirements.txt content.

        Returns:
            Dict with batch_id and list of execution results.
        """
        batch_id = generate_batch_id()
        executions = []

        for file_path in files:
            filename = Path(file_path).name
            execution_args = list(args or []) + [filename]

            # Create execution with batch_id
            result = self.client.create_execution(
                script_content=script_content,
                runtime=runtime,
                args=execution_args,
                env_vars=env_vars,
                input_files=[filename],
                batch_id=batch_id,
                requirements_content=requirements_content,
            )

            # Upload the file if upload URL provided
            upload_urls = result.get("upload_urls", {})
            if upload_urls and filename in upload_urls:
                upload_file_to_minio(file_path, upload_urls[filename])

            executions.append({
                "file": filename,
                "execution_id": result.get("execution_id"),
                "status": result.get("status"),
            })

        return {
            "batch_id": batch_id,
            "total_files": len(files),
            "executions": executions,
        }
