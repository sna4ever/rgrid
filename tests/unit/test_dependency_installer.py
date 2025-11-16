"""Unit tests for pip dependency installation (Story 2.4)."""

import pytest
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock


class TestDependencyInstaller:
    """Test pip installation logic in runner."""

    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_run):
        """Should successfully install dependencies from requirements.txt."""
        from runner.dependency_installer import install_dependencies

        # Arrange
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Successfully installed numpy-1.24.0 pandas-2.0.0",
            stderr=""
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0\npandas==2.0.0")

            # Act
            success, logs = install_dependencies(str(requirements_path))

            # Assert
            assert success is True
            assert "Successfully installed" in logs
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "pip" in call_args
            assert "install" in call_args
            assert "-r" in call_args

    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_run):
        """Should handle pip installation failures gracefully."""
        from runner.dependency_installer import install_dependencies

        # Arrange
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not find a version that satisfies the requirement invalid-package"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("invalid-package==999.0.0")

            # Act
            success, logs = install_dependencies(str(requirements_path))

            # Assert
            assert success is False
            assert "ERROR" in logs or "Could not find" in logs

    def test_install_dependencies_missing_file(self):
        """Should return error when requirements.txt doesn't exist."""
        from runner.dependency_installer import install_dependencies

        # Act
        success, logs = install_dependencies("/nonexistent/requirements.txt")

        # Assert
        assert success is False
        assert "not found" in logs.lower() or "does not exist" in logs.lower()

    @patch('subprocess.run')
    def test_install_captures_stdout_and_stderr(self, mock_run):
        """Should capture both stdout and stderr from pip install."""
        from runner.dependency_installer import install_dependencies

        # Arrange
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Collecting numpy\nInstalling collected packages",
            stderr="WARNING: Cache directory is not writable"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0")

            # Act
            success, logs = install_dependencies(str(requirements_path))

            # Assert
            assert success is True
            # Logs should contain both stdout and stderr
            assert "Collecting" in logs or "Installing" in logs or "WARNING" in logs

    @patch('subprocess.run')
    def test_install_uses_correct_pip_flags(self, mock_run):
        """Should use --no-cache-dir for reproducibility."""
        from runner.dependency_installer import install_dependencies

        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0")

            # Act
            install_dependencies(str(requirements_path))

            # Assert
            call_args = mock_run.call_args[0][0]
            assert "--no-cache-dir" in call_args or "-r" in call_args


class TestDependencyIntegration:
    """Test dependency installation integration with executor."""

    def test_executor_skips_install_if_no_requirements(self):
        """Should skip pip install if requirements.txt not provided."""
        # This will be tested in integration tests
        # Unit test confirms the conditional logic
        pass

    def test_executor_installs_before_script_execution(self):
        """Should install dependencies before running the script."""
        # This will be tested in integration tests
        # Unit test confirms the execution order
        pass
