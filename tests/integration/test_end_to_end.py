"""
End-to-end walking skeleton test.

Tests the complete flow: CLI -> API -> Execution
"""

import pytest
from pathlib import Path
import tempfile
from click.testing import CliRunner


@pytest.fixture
def temp_script() -> Path:
    """Create temporary test script."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("print('Hello from RGrid!')\n")
        return Path(f.name)


class TestWalkingSkeleton:
    """Test end-to-end walking skeleton functionality."""

    def test_cli_init_command(self) -> None:
        """Test that rgrid init works."""
        from rgrid.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Run init with defaults
            result = runner.invoke(main, ["init"], input="n\n")
            assert result.exit_code == 0 or "Initialization" in result.output

    def test_cli_run_command_requires_init(self, temp_script: Path) -> None:
        """Test that rgrid run requires initialization."""
        from rgrid.cli import main
        from rgrid.config import RGridConfig

        # Ensure no credentials exist
        config = RGridConfig()
        if config.credentials_file.exists():
            config.credentials_file.unlink()

        runner = CliRunner()
        result = runner.invoke(main, ["run", str(temp_script)])

        # Should fail without credentials
        assert result.exit_code != 0
        assert "credentials" in result.output.lower() or "init" in result.output.lower()

    def test_api_create_execution(self) -> None:
        """Test API execution creation endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Create execution
        response = client.post(
            "/api/v1/executions",
            json={
                "script_content": "print('test')",
                "runtime": "python:3.11",
                "args": [],
                "env_vars": {},
            },
            headers={"Authorization": "Bearer sk_test_123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data
        assert data["status"] == "queued"

    def test_docker_executor(self) -> None:
        """Test Docker executor can run simple script."""
        import docker

        # Check if Docker is available
        try:
            client = docker.from_env()
            client.ping()
        except Exception:
            pytest.skip("Docker not available")

        from runner.executor import DockerExecutor

        executor = DockerExecutor()

        # Execute simple script
        exit_code, stdout, stderr = executor.execute_script(
            script_content="print('Hello from Docker')\n",
            runtime="python:3.11-slim",
            args=[],
            env_vars={},
        )

        assert exit_code == 0
        assert "Hello from Docker" in stdout

        executor.close()


class TestAPIAuth:
    """Test API authentication."""

    def test_api_requires_auth(self) -> None:
        """Test API requires authentication."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Try without auth
        response = client.post(
            "/api/v1/executions",
            json={"script_content": "print('test')", "runtime": "python:3.11"},
        )

        assert response.status_code == 401

    def test_api_accepts_valid_key(self) -> None:
        """Test API accepts valid API key."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Try with valid format
        response = client.post(
            "/api/v1/executions",
            json={
                "script_content": "print('test')",
                "runtime": "python:3.11",
                "args": [],
                "env_vars": {},
            },
            headers={"Authorization": "Bearer sk_dev_test123"},
        )

        assert response.status_code == 200
