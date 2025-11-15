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
    ) -> tuple[int, str, str]:
        """
        Execute script in Docker container.

        Args:
            script_content: Python script source code
            runtime: Docker image to use
            args: Script arguments
            env_vars: Environment variables

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

            # Run container
            try:
                container: Container = self.client.containers.run(
                    runtime,
                    command=cmd,
                    volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
                    environment=env_vars,
                    detach=True,
                    remove=False,
                    network_mode="none",  # No network access by default
                )

                # Wait for completion
                result = container.wait()
                exit_code = result.get("StatusCode", -1)

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
