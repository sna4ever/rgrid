"""Docker container executor."""

import docker
from docker.models.containers import Container
from typing import Optional
from pathlib import Path
import tempfile


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

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        args = args or []
        env_vars = env_vars or {}

        # Create temporary directory for script
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(script_content)

            # Prepare command
            cmd = ["python", "/workspace/script.py"] + args

            # Calculate resource limits
            mem_limit_bytes = mem_limit_mb * 1024 * 1024  # Convert MB to bytes
            cpu_quota = int(cpu_count * 100000)  # 100000 = 1 CPU
            cpu_period = 100000  # Standard period

            # Run container with resource limits
            try:
                container: Container = self.client.containers.run(
                    runtime,
                    command=cmd,
                    volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
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
