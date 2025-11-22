"""Unit tests for batch retry functionality (Story 5-6).

Tests the `rgrid retry --batch <batch-id> --failed-only` command.
"""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from rgrid.commands.retry import retry


class TestBatchRetry:
    """Test retry command with --batch option."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        with patch("rgrid.commands.retry.get_client") as mock_get_client:
            client = MagicMock()
            mock_get_client.return_value = client
            yield client

    def test_batch_retry_failed_only_retries_only_failed_executions(
        self, runner, mock_client
    ):
        """When --failed-only is set, only failed executions should be retried."""
        # Arrange - batch with mixed statuses
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "completed"},
            {"execution_id": "exec_002", "status": "failed"},
            {"execution_id": "exec_003", "status": "completed"},
            {"execution_id": "exec_004", "status": "failed"},
        ]
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_new",
            "status": "queued",
        }

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert
        assert result.exit_code == 0
        # Should only retry the 2 failed executions
        assert mock_client.retry_execution.call_count == 2
        mock_client.retry_execution.assert_any_call("exec_002")
        mock_client.retry_execution.assert_any_call("exec_004")

    def test_batch_retry_without_failed_only_retries_all(self, runner, mock_client):
        """Without --failed-only, all executions should be retried."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "completed"},
            {"execution_id": "exec_002", "status": "failed"},
        ]
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_new",
            "status": "queued",
        }

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123"])

        # Assert
        assert result.exit_code == 0
        # Should retry all executions
        assert mock_client.retry_execution.call_count == 2

    def test_batch_retry_displays_summary(self, runner, mock_client):
        """Batch retry should display a summary of retried executions."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "failed"},
            {"execution_id": "exec_002", "status": "failed"},
        ]
        mock_client.retry_execution.side_effect = [
            {"execution_id": "exec_new_001", "status": "queued"},
            {"execution_id": "exec_new_002", "status": "queued"},
        ]

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert
        assert result.exit_code == 0
        assert "2" in result.output  # Should show count of retried
        assert "batch_123" in result.output

    def test_batch_retry_no_failed_executions(self, runner, mock_client):
        """When no failed executions exist, should show appropriate message."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "completed"},
            {"execution_id": "exec_002", "status": "completed"},
        ]

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert
        assert result.exit_code == 0
        # Should indicate no failures to retry
        assert "no failed" in result.output.lower() or "0" in result.output

    def test_batch_retry_empty_batch(self, runner, mock_client):
        """When batch has no executions, should show appropriate message."""
        # Arrange
        mock_client.get_batch_executions.return_value = []

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert
        # Should handle empty batch gracefully
        assert "no" in result.output.lower() or "0" in result.output

    def test_batch_retry_creates_new_execution_ids(self, runner, mock_client):
        """Retried executions should get new execution IDs."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_old", "status": "failed"},
        ]
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_new",
            "status": "queued",
        }

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert
        assert result.exit_code == 0
        assert "exec_new" in result.output

    def test_batch_retry_invalid_batch_id(self, runner, mock_client):
        """Should handle invalid batch ID gracefully."""
        # Arrange
        mock_client.get_batch_executions.side_effect = Exception("Batch not found")

        # Act
        result = runner.invoke(retry, ["--batch", "invalid_batch"])

        # Assert
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_batch_retry_partial_failure(self, runner, mock_client):
        """If some retries fail, should continue with others and report."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "failed"},
            {"execution_id": "exec_002", "status": "failed"},
        ]
        # First retry succeeds, second fails
        mock_client.retry_execution.side_effect = [
            {"execution_id": "exec_new", "status": "queued"},
            Exception("Retry failed"),
        ]

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert - should continue and report partial success
        assert "1" in result.output  # At least one succeeded

    def test_single_execution_retry_still_works(self, runner, mock_client):
        """Original single execution retry should still work."""
        # Arrange
        mock_client.get_execution.return_value = {
            "execution_id": "exec_123",
            "status": "failed",
        }
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_new",
            "status": "queued",
        }

        # Act
        result = runner.invoke(retry, ["exec_123"])

        # Assert
        assert result.exit_code == 0
        mock_client.retry_execution.assert_called_once_with("exec_123")

    def test_batch_and_execution_id_mutually_exclusive(self, runner, mock_client):
        """Cannot provide both --batch and execution_id."""
        # Act
        result = runner.invoke(retry, ["exec_123", "--batch", "batch_123"])

        # Assert - should show error
        assert result.exit_code != 0 or "cannot" in result.output.lower() or "error" in result.output.lower()

    def test_execution_id_required_without_batch(self, runner, mock_client):
        """Execution ID is required when --batch is not provided."""
        # Act
        result = runner.invoke(retry, [])

        # Assert - missing argument error
        assert result.exit_code != 0

    def test_batch_retry_skips_running_executions(self, runner, mock_client):
        """--failed-only should skip running executions."""
        # Arrange
        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_001", "status": "running"},
            {"execution_id": "exec_002", "status": "failed"},
            {"execution_id": "exec_003", "status": "queued"},
        ]
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_new",
            "status": "queued",
        }

        # Act
        result = runner.invoke(retry, ["--batch", "batch_123", "--failed-only"])

        # Assert - should only retry the failed one
        assert mock_client.retry_execution.call_count == 1
        mock_client.retry_execution.assert_called_with("exec_002")
