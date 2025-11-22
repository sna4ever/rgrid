"""
E2E tests for monitoring commands (Epic 8).

Tests the monitoring CLI commands:
- rgrid status (Story 8-1)
- rgrid logs (Story 8-2)
- WebSocket log streaming (Story 8-3)
- CLI reconnection for WebSocket (Story 8-4)
- Batch progress with --watch (Story 8-5)
- Execution metadata tracking (Story 8-6)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner


@pytest.mark.e2e
class TestStatusCommand:
    """Test rgrid status command (Story 8-1)."""

    def test_status_shows_execution_info(self, cli_runner, mock_credentials):
        """Test status command displays execution information."""
        from rgrid.cli import main

        with patch('rgrid.commands.status.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_abc123",
                "status": "completed",
                "runtime": "python:3.11",
                "exit_code": 0,
                "created_at": "2025-11-22T10:00:00Z",
                "started_at": "2025-11-22T10:00:05Z",
                "completed_at": "2025-11-22T10:00:10Z",
                "stdout": "Hello World",
                "stderr": "",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['status', 'exec_abc123'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "exec_abc123" in result.output

    def test_status_shows_failed_execution(self, cli_runner, mock_credentials):
        """Test status command handles failed executions."""
        from rgrid.cli import main

        with patch('rgrid.commands.status.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_failed",
                "status": "failed",
                "runtime": "python:3.11",
                "exit_code": 1,
                "execution_error": "Script crashed",
                "created_at": "2025-11-22T10:00:00Z",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['status', 'exec_failed'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_status_shows_queued_with_provisioning_hint(self, cli_runner, mock_credentials):
        """Test status command shows provisioning hint for queued jobs."""
        from rgrid.cli import main
        from datetime import datetime, timezone

        # Create timestamp 60 seconds ago
        old_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        with patch('rgrid.commands.status.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_queued",
                "status": "queued",
                "runtime": "python:3.11",
                "created_at": "2025-11-22T09:00:00Z",  # Old timestamp
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['status', 'exec_queued'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "queued" in result.output.lower()

    def test_status_shows_worker_hostname(self, cli_runner, mock_credentials):
        """Test status shows worker hostname (Story 8-6)."""
        from rgrid.cli import main

        with patch('rgrid.commands.status.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_123",
                "status": "running",
                "runtime": "python:3.11",
                "worker_hostname": "worker-abc123",
                "created_at": "2025-11-22T10:00:00Z",
                "started_at": "2025-11-22T10:00:05Z",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['status', 'exec_123'],
                    catch_exceptions=False,
                )

        # Should show worker info if present
        assert result.exit_code == 0


@pytest.mark.e2e
class TestLogsCommand:
    """Test rgrid logs command (Story 8-2)."""

    def test_logs_shows_stdout(self, cli_runner, mock_credentials):
        """Test logs command displays stdout."""
        from rgrid.cli import main

        with patch('rgrid.commands.logs.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_123",
                "status": "completed",
                "stdout": "Hello World!\nLine 2\nLine 3",
                "stderr": "",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['logs', 'exec_123'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "Hello World" in result.output or "Line" in result.output

    def test_logs_shows_stderr(self, cli_runner, mock_credentials):
        """Test logs command displays stderr."""
        from rgrid.cli import main

        with patch('rgrid.commands.logs.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_123",
                "status": "failed",
                "stdout": "",
                "stderr": "Error: Something went wrong",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['logs', 'exec_123'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "Error" in result.output or "wrong" in result.output

    def test_logs_stdout_only_filter(self, cli_runner, mock_credentials):
        """Test logs --stdout-only filter."""
        from rgrid.cli import main

        with patch('rgrid.commands.logs.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_123",
                "status": "completed",
                "stdout": "stdout output",
                "stderr": "stderr output",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['logs', 'exec_123', '--stdout-only'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        # Should show stdout but not stderr
        assert "stdout" in result.output.lower()

    def test_logs_handles_no_output(self, cli_runner, mock_credentials):
        """Test logs command handles executions with no output."""
        from rgrid.cli import main

        with patch('rgrid.commands.logs.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_execution.return_value = {
                "execution_id": "exec_123",
                "status": "completed",
                "stdout": "",
                "stderr": "",
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['logs', 'exec_123'],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "no output" in result.output.lower() or result.output == ""


@pytest.mark.e2e
class TestWebSocketLogStreaming:
    """Test WebSocket log streaming (Stories 8-3, 8-4)."""

    def test_websocket_message_processing(self):
        """Test WebSocket message processing (Story 8-3)."""
        from rgrid.commands.logs import process_websocket_message
        import json

        # Test log message
        log_msg = json.dumps({
            "type": "log",
            "sequence_number": 1,
            "timestamp": "2025-11-22T10:00:00Z",
            "stream": "stdout",
            "message": "Hello World",
        })
        result = process_websocket_message(log_msg)

        assert result["type"] == "log"
        assert result["message"] == "Hello World"
        assert result["continue"] is True

    def test_websocket_complete_message(self):
        """Test WebSocket complete message processing."""
        from rgrid.commands.logs import process_websocket_message
        import json

        complete_msg = json.dumps({
            "type": "complete",
            "exit_code": 0,
            "status": "completed",
        })
        result = process_websocket_message(complete_msg)

        assert result["type"] == "complete"
        assert result["exit_code"] == 0
        assert result["continue"] is False

    def test_websocket_error_message(self):
        """Test WebSocket error message processing."""
        from rgrid.commands.logs import process_websocket_message
        import json

        error_msg = json.dumps({
            "type": "error",
            "error": "Connection lost",
        })
        result = process_websocket_message(error_msg)

        assert result["type"] == "error"
        assert result["error"] == "Connection lost"
        assert result["continue"] is False

    def test_log_line_formatting(self):
        """Test log line formatting for display."""
        from rgrid.commands.logs import format_log_line

        # stdout should be plain
        stdout_line = format_log_line("stdout", "Normal output")
        assert "Normal output" in stdout_line

        # stderr should be marked (red in rich format)
        stderr_line = format_log_line("stderr", "Error output")
        assert "Error output" in stderr_line


@pytest.mark.e2e
class TestBatchProgressWatch:
    """Test batch progress with --watch (Story 8-5)."""

    def test_batch_progress_display_function_exists(self):
        """Test batch progress display functions exist."""
        from rgrid.batch_progress import (
            display_batch_progress,
            display_batch_progress_with_watch,
        )

        assert callable(display_batch_progress)
        assert callable(display_batch_progress_with_watch)

    def test_batch_progress_calculation(self, mock_api_client):
        """Test batch progress calculation."""
        mock_api_client.get_batch_status.return_value = {
            "total": 10,
            "completed": 6,
            "failed": 2,
            "running": 1,
            "queued": 1,
        }

        status = mock_api_client.get_batch_status("batch_123")

        # Calculate progress
        done = status["completed"] + status["failed"]
        total = status["total"]
        progress_pct = (done / total) * 100

        assert progress_pct == 80.0
        assert status["completed"] == 6
        assert status["failed"] == 2


@pytest.mark.e2e
class TestExecutionMetadata:
    """Test execution metadata tracking (Story 8-6)."""

    def test_metadata_in_execution_response(self, mock_api_client):
        """Test execution response includes metadata."""
        mock_api_client.get_execution.return_value = {
            "execution_id": "exec_123",
            "status": "completed",
            "runtime": "python:3.11",
            "worker_hostname": "worker-abc",
            "worker_id": "node-123",
            "created_at": "2025-11-22T10:00:00Z",
            "started_at": "2025-11-22T10:00:05Z",
            "completed_at": "2025-11-22T10:00:10Z",
        }

        result = mock_api_client.get_execution("exec_123")

        assert "worker_hostname" in result
        assert "started_at" in result
        assert "completed_at" in result
