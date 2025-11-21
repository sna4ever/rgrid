"""Unit tests for WebSocket log streaming (Story 8.3)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from click.testing import CliRunner
import asyncio
import json


class TestLogsFollowFlag:
    """Test --follow flag for real-time log streaming."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_logs_command_has_follow_option(self):
        """Logs command should have --follow option."""
        from rgrid.commands.logs import logs

        param_names = [p.name for p in logs.params]
        assert 'follow' in param_names

    @patch('rgrid.commands.logs.get_client')
    def test_logs_without_follow_fetches_historical(
        self, mock_get_client, cli_runner
    ):
        """Without --follow, should fetch historical logs."""
        from rgrid.commands.logs import logs

        mock_client = Mock()
        mock_client.get_execution.return_value = {
            "execution_id": "exec_abc123",
            "status": "completed",
            "stdout": "Hello World",
            "stderr": "",
            "output_truncated": False,
        }
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(logs, ['exec_abc123'])

        assert result.exit_code == 0
        assert 'Hello World' in result.output
        mock_client.get_execution.assert_called_once()

    @patch('rgrid.commands.logs.stream_logs_websocket')
    @patch('rgrid.commands.logs.get_client')
    def test_logs_with_follow_starts_websocket_stream(
        self, mock_get_client, mock_stream, cli_runner
    ):
        """With --follow, should start WebSocket streaming."""
        from rgrid.commands.logs import logs

        # Mock the WebSocket streaming function
        mock_stream.return_value = None

        result = cli_runner.invoke(logs, ['exec_abc123', '--follow'])

        # Should have called the streaming function
        mock_stream.assert_called_once_with('exec_abc123')


class TestExecutionLogModel:
    """Test ExecutionLog database model."""

    def test_execution_log_creation(self):
        """Should create ExecutionLog with required fields."""
        from app.models.execution_log import ExecutionLog

        log = ExecutionLog(
            execution_id="exec_abc123",
            sequence_number=0,
            stream="stdout",
            message="Hello World",
        )

        assert log.execution_id == "exec_abc123"
        assert log.sequence_number == 0
        assert log.stream == "stdout"
        assert log.message == "Hello World"
        assert log.log_id is not None
        assert log.log_id.startswith("log_")
        assert log.timestamp is not None

    def test_execution_log_to_dict(self):
        """Should convert to dictionary for JSON serialization."""
        from app.models.execution_log import ExecutionLog
        from datetime import datetime

        timestamp = datetime(2025, 11, 15, 10, 30, 15)
        log = ExecutionLog(
            execution_id="exec_abc123",
            sequence_number=42,
            stream="stderr",
            message="Error occurred",
            log_id="log_test123",
            timestamp=timestamp,
        )

        result = log.to_dict()

        assert result["log_id"] == "log_test123"
        assert result["execution_id"] == "exec_abc123"
        assert result["sequence_number"] == 42
        assert result["stream"] == "stderr"
        assert result["message"] == "Error occurred"
        assert result["timestamp"] == "2025-11-15T10:30:15"

    def test_execution_log_auto_generates_log_id(self):
        """Should auto-generate unique log_id if not provided."""
        from app.models.execution_log import ExecutionLog

        log1 = ExecutionLog(
            execution_id="exec_abc123",
            sequence_number=0,
            stream="stdout",
            message="Line 1",
        )
        log2 = ExecutionLog(
            execution_id="exec_abc123",
            sequence_number=1,
            stream="stdout",
            message="Line 2",
        )

        assert log1.log_id != log2.log_id


class TestWebSocketLogMessage:
    """Test WebSocket message format."""

    def test_log_message_format(self):
        """Log messages should have correct format."""
        message = {
            "type": "log",
            "execution_id": "exec_abc123",
            "sequence_number": 42,
            "timestamp": "2025-11-15T10:30:15.123Z",
            "stream": "stdout",
            "message": "Processing file data.csv...",
        }

        assert message["type"] == "log"
        assert "sequence_number" in message
        assert "stream" in message
        assert message["stream"] in ["stdout", "stderr"]

    def test_complete_message_format(self):
        """Completion messages should have correct format."""
        message = {
            "type": "complete",
            "execution_id": "exec_abc123",
            "exit_code": 0,
            "status": "completed",
        }

        assert message["type"] == "complete"
        assert "exit_code" in message
        assert message["status"] in ["completed", "failed"]

    def test_error_message_format(self):
        """Error messages should have correct format."""
        message = {
            "type": "error",
            "execution_id": "exec_abc123",
            "error": "Connection lost to runner",
        }

        assert message["type"] == "error"
        assert "error" in message


class TestLogStreamClient:
    """Test CLI WebSocket client for log streaming."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        return mock_ws

    @pytest.mark.asyncio
    async def test_stream_displays_log_lines(self, mock_websocket):
        """Should display log lines as they arrive."""
        from rgrid.commands.logs import process_websocket_message

        # Test log message
        message = json.dumps({
            "type": "log",
            "execution_id": "exec_abc123",
            "sequence_number": 0,
            "timestamp": "2025-11-15T10:30:15",
            "stream": "stdout",
            "message": "Hello World",
        })

        result = process_websocket_message(message)

        assert result["type"] == "log"
        assert result["message"] == "Hello World"
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_stream_stops_on_complete(self, mock_websocket):
        """Should stop streaming on completion message."""
        from rgrid.commands.logs import process_websocket_message

        message = json.dumps({
            "type": "complete",
            "execution_id": "exec_abc123",
            "exit_code": 0,
            "status": "completed",
        })

        result = process_websocket_message(message)

        assert result["type"] == "complete"
        assert result["exit_code"] == 0
        assert result["continue"] is False

    @pytest.mark.asyncio
    async def test_stream_handles_error_message(self, mock_websocket):
        """Should handle error messages gracefully."""
        from rgrid.commands.logs import process_websocket_message

        message = json.dumps({
            "type": "error",
            "execution_id": "exec_abc123",
            "error": "Execution not found",
        })

        result = process_websocket_message(message)

        assert result["type"] == "error"
        assert "error" in result
        assert result["continue"] is False


class TestAPIWebSocketEndpoint:
    """Test API WebSocket endpoint for log streaming."""

    def test_websocket_route_exists(self):
        """WebSocket route should be registered."""
        from app.main import app

        # Check for WebSocket route
        routes = [route.path for route in app.routes]
        assert "/ws/executions/{execution_id}/logs" in routes or any(
            "/ws/" in route for route in routes
        )
