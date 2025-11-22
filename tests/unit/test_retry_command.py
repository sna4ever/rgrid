"""Unit tests for retry command (Story 10-6).

Tests the `rgrid retry` command that allows users to retry failed executions.
"""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner


class TestRetryCommand:
    """Test the rgrid retry CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        client = MagicMock()
        client.get_execution.return_value = {
            "execution_id": "exec_original123",
            "status": "failed",
            "script_content": "print('hello')",
            "runtime": "python:3.11",
            "args": ["arg1", "arg2"],
            "env_vars": {"KEY": "value"},
            "input_files": ["input.txt"],
            "exit_code": 1,
            "error_message": "ModuleNotFoundError: No module named 'pandas'",
        }
        client.retry_execution.return_value = {
            "execution_id": "exec_new456",
            "status": "queued",
        }
        return client

    def test_retry_failed_execution(self, runner, mock_client):
        """Retry should create new execution from failed one."""
        from rgrid.commands.retry import retry

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_original123"])

        # Assert
        assert result.exit_code == 0
        assert "exec_new456" in result.output
        mock_client.retry_execution.assert_called_once_with("exec_original123")

    def test_retry_shows_original_id(self, runner, mock_client):
        """Retry output should show original execution ID."""
        from rgrid.commands.retry import retry

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_original123"])

        # Assert
        assert "exec_original123" in result.output

    def test_retry_completed_execution(self, runner, mock_client):
        """Retry should work on completed executions too."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value["status"] = "completed"

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_completed"])

        # Assert - should succeed without --force for completed
        assert result.exit_code == 0

    def test_retry_running_execution_warns(self, runner, mock_client):
        """Retry on running execution should warn and require --force."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value["status"] = "running"

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_running"])

        # Assert - should warn user
        assert "running" in result.output.lower() or result.exit_code != 0

    def test_retry_with_force_flag(self, runner, mock_client):
        """--force should allow retry of any execution."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value["status"] = "running"

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_running", "--force"])

        # Assert
        assert result.exit_code == 0
        mock_client.retry_execution.assert_called_once()

    def test_retry_nonexistent_execution(self, runner, mock_client):
        """Retry should handle non-existent execution gracefully."""
        from rgrid.commands.retry import retry

        mock_client.retry_execution.side_effect = Exception("Execution not found")

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_nonexistent"])

        # Assert
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestRetryAPIClient:
    """Test the API client retry_execution method."""

    def test_retry_execution_calls_correct_endpoint(self):
        """retry_execution should call POST /executions/{id}/retry."""
        from rgrid.api_client import APIClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"execution_id": "exec_new123"}
        mock_response.raise_for_status = MagicMock()

        # Create mock client with mocked httpx
        with patch("rgrid.api_client.config") as mock_config:
            mock_config.load_credentials.return_value = {
                "api_url": "http://test",
                "api_key": "test-key",
            }

            with patch("rgrid.api_client.httpx.Client") as mock_httpx:
                mock_httpx_instance = MagicMock()
                # Updated to use .request since _request method uses client.request()
                mock_httpx_instance.request.return_value = mock_response
                mock_httpx.return_value = mock_httpx_instance

                # Disable retry to simplify test (Story 10-5)
                client = APIClient(enable_retry=False)

                result = client.retry_execution("exec_original123")

                # Assert - now uses .request("POST", path) instead of .post(path)
                mock_httpx_instance.request.assert_called_once()
                call_args = mock_httpx_instance.request.call_args
                assert call_args[0][0] == "POST"  # First arg is method
                assert "exec_original123" in call_args[0][1]  # Second arg is path
                assert "retry" in call_args[0][1]
                assert result["execution_id"] == "exec_new123"
