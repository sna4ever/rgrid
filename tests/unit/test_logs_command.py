"""Unit tests for rgrid logs command (Story 8.2)."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner


class TestLogsCommand:
    """Test rgrid logs command functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_api_response_with_output(self):
        """Mock API response with stdout and stderr."""
        return {
            "execution_id": "exec_abc123",
            "status": "completed",
            "stdout": "Hello World\nLine 2\nLine 3",
            "stderr": "Warning: something happened",
            "output_truncated": False,
        }

    @pytest.fixture
    def mock_api_response_stdout_only(self):
        """Mock API response with only stdout."""
        return {
            "execution_id": "exec_abc123",
            "status": "completed",
            "stdout": "Hello World\nScript completed successfully",
            "stderr": "",
            "output_truncated": False,
        }

    @pytest.fixture
    def mock_api_response_stderr_only(self):
        """Mock API response with only stderr."""
        return {
            "execution_id": "exec_failed",
            "status": "failed",
            "stdout": "",
            "stderr": "Error: Module not found\nTraceback follows...",
            "output_truncated": False,
        }

    @pytest.fixture
    def mock_api_response_truncated(self):
        """Mock API response with truncated output."""
        return {
            "execution_id": "exec_big",
            "status": "completed",
            "stdout": "Lots of output here...",
            "stderr": "",
            "output_truncated": True,
        }

    @pytest.fixture
    def mock_api_response_no_output(self):
        """Mock API response with no output."""
        return {
            "execution_id": "exec_empty",
            "status": "completed",
            "stdout": "",
            "stderr": "",
            "output_truncated": False,
        }

    @patch('rgrid.commands.logs.get_client')
    def test_logs_displays_stdout_and_stderr(self, mock_get_client, cli_runner, mock_api_response_with_output):
        """Should display both stdout and stderr."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_with_output
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_abc123'])

        # Assert
        assert result.exit_code == 0
        assert 'Hello World' in result.output
        assert 'Warning: something happened' in result.output
        mock_client.get_execution.assert_called_once_with('exec_abc123')

    @patch('rgrid.commands.logs.get_client')
    def test_logs_stdout_only_flag(self, mock_get_client, cli_runner, mock_api_response_with_output):
        """Should display only stdout with --stdout-only flag."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_with_output
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_abc123', '--stdout-only'])

        # Assert
        assert result.exit_code == 0
        assert 'Hello World' in result.output
        assert 'Warning: something happened' not in result.output

    @patch('rgrid.commands.logs.get_client')
    def test_logs_stderr_only_flag(self, mock_get_client, cli_runner, mock_api_response_with_output):
        """Should display only stderr with --stderr-only flag."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_with_output
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_abc123', '--stderr-only'])

        # Assert
        assert result.exit_code == 0
        assert 'Hello World' not in result.output
        assert 'Warning: something happened' in result.output

    @patch('rgrid.commands.logs.get_client')
    def test_logs_no_output_message(self, mock_get_client, cli_runner, mock_api_response_no_output):
        """Should show message when no output available."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_no_output
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_empty'])

        # Assert
        assert result.exit_code == 0
        assert 'No output available' in result.output

    @patch('rgrid.commands.logs.get_client')
    def test_logs_truncation_warning(self, mock_get_client, cli_runner, mock_api_response_truncated):
        """Should show truncation warning when output was truncated."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_truncated
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_big'])

        # Assert
        assert result.exit_code == 0
        assert 'truncated' in result.output.lower()

    @patch('rgrid.commands.logs.get_client')
    def test_logs_handles_api_error(self, mock_get_client, cli_runner):
        """Should handle API errors gracefully."""
        from rgrid.commands.logs import logs

        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.get_execution.side_effect = Exception("Execution not found")
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_notfound'])

        # Assert
        assert result.exit_code != 0
        assert 'Error' in result.output

    def test_logs_requires_execution_id(self, cli_runner):
        """Should require execution_id argument."""
        from rgrid.commands.logs import logs

        # Act - invoke without argument
        result = cli_runner.invoke(logs, [])

        # Assert
        assert result.exit_code != 0
        assert 'Missing argument' in result.output or 'EXECUTION_ID' in result.output

    @patch('rgrid.commands.logs.get_client')
    def test_logs_only_stdout_when_only_stdout_available(self, mock_get_client, cli_runner, mock_api_response_stdout_only):
        """Should display only stdout when that's all that's available."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_stdout_only
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_abc123'])

        # Assert
        assert result.exit_code == 0
        assert 'Hello World' in result.output
        # STDERR label should not appear when there's no stderr
        assert 'STDERR' not in result.output

    @patch('rgrid.commands.logs.get_client')
    def test_logs_only_stderr_when_only_stderr_available(self, mock_get_client, cli_runner, mock_api_response_stderr_only):
        """Should display only stderr when that's all that's available."""
        from rgrid.commands.logs import logs

        # Setup mock
        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_stderr_only
        mock_get_client.return_value = mock_client

        # Act
        result = cli_runner.invoke(logs, ['exec_failed'])

        # Assert
        assert result.exit_code == 0
        assert 'Error: Module not found' in result.output


class TestLogsCommandIntegration:
    """Test logs command is properly registered in CLI."""

    def test_logs_command_registered(self):
        """Logs command should be registered in main CLI."""
        from rgrid.cli import main

        # Check logs is in the command group
        assert 'logs' in main.commands

    def test_logs_command_has_help(self):
        """Logs command should have help text."""
        from rgrid.commands.logs import logs

        assert logs.help is not None or logs.__doc__ is not None

    def test_logs_command_has_options(self):
        """Logs command should have stdout-only and stderr-only options."""
        from rgrid.commands.logs import logs

        # Check options exist
        param_names = [p.name for p in logs.params]
        assert 'stdout_only' in param_names
        assert 'stderr_only' in param_names
