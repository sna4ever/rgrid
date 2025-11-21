"""Unit tests for rgrid status command (Story 8.1)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from datetime import datetime, timezone


class TestStatusCommand:
    """Test rgrid status command functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_api_response_completed(self):
        """Mock API response for completed execution."""
        return {
            "execution_id": "exec_abc123",
            "status": "completed",
            "runtime": "python:3.11",
            "exit_code": 0,
            "created_at": "2025-01-15T10:00:00Z",
            "started_at": "2025-01-15T10:00:05Z",
            "completed_at": "2025-01-15T10:00:15Z",
            "stdout": "Hello World",
            "stderr": "",
            "output_truncated": False,
        }

    @pytest.fixture
    def mock_api_response_failed(self):
        """Mock API response for failed execution."""
        return {
            "execution_id": "exec_failed123",
            "status": "failed",
            "runtime": "python:3.11",
            "exit_code": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "started_at": "2025-01-15T10:00:05Z",
            "completed_at": "2025-01-15T10:00:10Z",
            "stdout": "",
            "stderr": "Error: Module not found",
            "execution_error": "Script failed with exit code 1",
            "output_truncated": False,
        }

    @pytest.fixture
    def mock_api_response_running(self):
        """Mock API response for running execution."""
        return {
            "execution_id": "exec_running123",
            "status": "running",
            "runtime": "python:3.11",
            "created_at": "2025-01-15T10:00:00Z",
            "started_at": "2025-01-15T10:00:05Z",
        }

    @pytest.fixture
    def mock_api_response_queued(self):
        """Mock API response for queued execution."""
        return {
            "execution_id": "exec_queued123",
            "status": "queued",
            "runtime": "python:3.11",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch('rgrid.commands.status.get_client')
    def test_status_completed_execution(self, mock_get_client, cli_runner, mock_api_response_completed):
        """Should display status for completed execution."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_completed
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_abc123'])

        # Assert
        assert result.exit_code == 0
        assert 'exec_abc123' in result.output
        assert 'completed' in result.output
        assert 'python:3.11' in result.output
        mock_client.get_execution.assert_called_once_with('exec_abc123')

    @patch('rgrid.commands.status.get_client')
    def test_status_failed_execution(self, mock_get_client, cli_runner, mock_api_response_failed):
        """Should display status for failed execution with error message."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_failed
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_failed123'])

        # Assert
        assert result.exit_code == 0
        assert 'failed' in result.output
        assert 'Script failed' in result.output or 'Error' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_running_execution(self, mock_get_client, cli_runner, mock_api_response_running):
        """Should display status for running execution."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_running
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_running123'])

        # Assert
        assert result.exit_code == 0
        assert 'running' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_queued_execution(self, mock_get_client, cli_runner, mock_api_response_queued):
        """Should display status for queued execution."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_queued
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_queued123'])

        # Assert
        assert result.exit_code == 0
        assert 'queued' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_shows_exit_code(self, mock_get_client, cli_runner, mock_api_response_completed):
        """Should display exit code when available."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_completed
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_abc123'])

        # Assert
        assert 'Exit Code' in result.output
        assert '0' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_shows_duration(self, mock_get_client, cli_runner, mock_api_response_completed):
        """Should calculate and display duration for completed executions."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_completed
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_abc123'])

        # Assert
        assert 'Duration' in result.output
        # 10 seconds between started_at and completed_at
        assert '10' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_shows_logs_hint(self, mock_get_client, cli_runner, mock_api_response_completed):
        """Should show hint for viewing logs when output exists."""
        from rgrid.commands.status import status

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_completed
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_abc123'])

        # Assert
        assert 'rgrid logs' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_handles_api_error(self, mock_get_client, cli_runner):
        """Should handle API errors gracefully."""
        from rgrid.commands.status import status

        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.get_execution.side_effect = Exception("Connection refused")
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(status, ['exec_notfound'])

        # Assert
        assert result.exit_code != 0
        assert 'Error' in result.output

    def test_status_requires_execution_id(self, cli_runner):
        """Should require execution_id argument."""
        from rgrid.commands.status import status

        # Act - invoke without argument
        result = cli_runner.invoke(status, [])

        # Assert
        assert result.exit_code != 0
        assert 'Missing argument' in result.output or 'EXECUTION_ID' in result.output


class TestStatusCommandIntegration:
    """Test status command is properly registered in CLI."""

    def test_status_command_registered(self):
        """Status command should be registered in main CLI."""
        from rgrid.cli import main

        # Check status is in the command group
        assert 'status' in main.commands

    def test_status_command_has_help(self):
        """Status command should have help text."""
        from rgrid.commands.status import status

        assert status.help is not None or status.__doc__ is not None
