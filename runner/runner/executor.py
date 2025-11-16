"""Docker container executor."""

import docker
from docker.models.containers import Container
from typing import Optional, Dict
from pathlib import Path
import tempfile

from runner.file_handler import download_input_files, map_args_to_container_paths


class DockerExecutor:
    """Execute scripts in Docker containers."""

    def __init__(self) -> None:
        """Initialize Docker client."""
        self.client = docker.from_env()

    def execute_script(
        self,
        script_content: str,
        runtime: str = "python:3.11",
        args: Optional[list[str]] = None,
        env_vars: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
        mem_limit_mb: int = 512,
        cpu_count: float = 1.0,
        download_urls: Optional[Dict[str, str]] = None,
    ) -> tuple[int, str, str]:
        """
        Execute script in Docker container with resource limits.

        Args:
            script_content: Python script source code
            runtime: Docker image to use
            args: Script arguments
            env_vars: Environment variables
            timeout_seconds: Maximum execution time (default: 300s / 5min)
            mem_limit_mb: Memory limit in MB (default: 512MB)
            cpu_count: CPU cores to allocate (default: 1.0)
            download_urls: Presigned URLs for input files (Tier 4 - Story 2-5)

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        args = args or []
        env_vars = env_vars or {}
        download_urls = download_urls or {}

        # Create temporary directory for script and files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_path = tmpdir_path / "script.py"
            script_path.write_text(script_content)

            # Download input files if any (Tier 4 - Story 2-5)
            volumes = {str(tmpdir_path): {"bind": "/workspace", "mode": "ro"}}

            if download_urls:
                # Create /work directory for input files
                work_dir = tmpdir_path / "work"
                work_dir.mkdir()

                # Download files to /work
                downloaded_files = download_input_files(download_urls, work_dir)

                # Get list of input filenames
                input_filenames = list(downloaded_files.keys())

                # Map arguments to container paths
                container_args = map_args_to_container_paths(args, input_filenames)

                # Mount /work directory (read-write for input files)
                volumes[str(work_dir)] = {"bind": "/work", "mode": "rw"}
            else:
                container_args = args

            # Prepare command
            cmd = ["python", "/workspace/script.py"] + container_args

            # Calculate resource limits
            mem_limit_bytes = mem_limit_mb * 1024 * 1024  # Convert MB to bytes
            cpu_quota = int(cpu_count * 100000)  # 100000 = 1 CPU
            cpu_period = 100000  # Standard period

            # Run container with resource limits
            try:
                container: Container = self.client.containers.run(
                    runtime,
                    command=cmd,
                    volumes=volumes,
                    environment=env_vars,
                    detach=True,
                    remove=False,
                    network_mode="none",  # No network access by default
                    mem_limit=mem_limit_bytes,  # Memory limit
                    cpu_quota=cpu_quota,  # CPU quota
                    cpu_period=cpu_period,  # CPU period
                )

                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=timeout_seconds)
                    exit_code = result.get("StatusCode", -1)
                except Exception as timeout_error:
                    # Timeout or other error - kill container
                    container.kill()
                    container.remove()
                    return -1, "", f"Execution timeout ({timeout_seconds}s) or error: {str(timeout_error)}"

                # Get logs
                logs = container.logs(stdout=True, stderr=True)
                output = logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)

                # Clean up
                container.remove()

                # For walking skeleton, return combined output
                # In full implementation, separate stdout/stderr
                return exit_code, output, ""

            except Exception as e:
                return -1, "", str(e)

    def close(self) -> None:
        """Close Docker client."""
        self.client.close()
