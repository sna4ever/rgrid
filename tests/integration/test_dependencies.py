"""Integration tests for dependency installation (Story 2.4)."""

import pytest
import tempfile
from pathlib import Path
import docker


class TestDependencyInstallationIntegration:
    """End-to-end tests for requirements.txt installation."""

    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Check if Docker is available before running tests."""
        try:
            client = docker.from_env()
            client.ping()
        except Exception:
            pytest.skip("Docker not available")

    def test_script_without_requirements_txt(self):
        """Should execute successfully without requirements.txt."""
        from runner.executor import DockerExecutor

        # Arrange - Simple script without dependencies
        script_content = """
print("Hello from RGrid!")
print("No dependencies needed")
"""

        # Act - Execute without requirements.txt
        executor = DockerExecutor()
        try:
            exit_code, stdout, stderr, outputs = executor.execute_script(
                script_content=script_content,
                runtime="python:3.11-slim",
            )

            # Assert
            assert exit_code == 0
            assert "Hello from RGrid!" in stdout
            assert "No dependencies needed" in stdout

            # Should NOT have dependency installation section
            assert "Dependency Installation" not in stdout

        finally:
            executor.close()

    def test_dependency_installer_with_real_package(self):
        """Should successfully install a real lightweight package."""
        from runner.dependency_installer import install_dependencies

        # Arrange - Create temporary requirements file with lightweight package
        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = Path(tmpdir) / "requirements.txt"
            # Use a very small package for testing
            requirements_path.write_text("six==1.16.0")

            # Act
            success, logs = install_dependencies(str(requirements_path))

            # Assert
            assert success is True
            assert "successfully installed" in logs.lower() or "requirement already satisfied" in logs.lower()

    def test_cli_detects_requirements_txt(self):
        """Should detect requirements.txt in same directory as script."""
        from rgrid.utils.file_detection import detect_requirements_file

        # Arrange - Create script and requirements.txt in temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "test_script.py"
            script_path.write_text("print('test')")

            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0")

            # Act
            result = detect_requirements_file(str(script_path))

            # Assert
            assert result is not None
            assert Path(result).name == "requirements.txt"
            assert Path(result).parent == Path(tmpdir)
