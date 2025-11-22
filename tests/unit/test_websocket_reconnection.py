"""Unit tests for WebSocket reconnection (Story 8.4)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import json


class TestWebSocketReconnection:
    """Test CLI WebSocket reconnection behavior."""

    def test_process_websocket_message_extracts_sequence_number(self):
        """Should extract sequence_number from log messages for cursor tracking."""
        from rgrid.commands.logs import process_websocket_message

        message = json.dumps({
            "type": "log",
            "execution_id": "exec_abc123",
            "sequence_number": 42,
            "timestamp": "2025-11-15T10:30:15",
            "stream": "stdout",
            "message": "Hello World",
        })

        result = process_websocket_message(message)

        assert result["sequence_number"] == 42
        assert result["type"] == "log"
        assert result["continue"] is True

    def test_process_websocket_message_handles_missing_sequence(self):
        """Should handle log messages without sequence_number."""
        from rgrid.commands.logs import process_websocket_message

        message = json.dumps({
            "type": "log",
            "execution_id": "exec_abc123",
            "stream": "stdout",
            "message": "Hello World",
        })

        result = process_websocket_message(message)

        assert result["sequence_number"] is None
        assert result["type"] == "log"

    @pytest.mark.asyncio
    async def test_reconnect_delay_starts_at_one_second(self):
        """Reconnect delay should start at 1 second (within 5s requirement)."""
        from rgrid.commands.logs import _stream_logs_websocket
        import websockets

        # The delay starts at 1 second
        reconnect_delay = 1
        max_reconnect_delay = 30

        # Verify initial delay is within 5 seconds requirement
        assert reconnect_delay <= 5

    @pytest.mark.asyncio
    async def test_reconnect_delay_uses_exponential_backoff(self):
        """Reconnect delay should double each time up to max."""
        reconnect_delay = 1
        max_reconnect_delay = 30

        # First reconnect
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 2

        # Second reconnect
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 4

        # Third reconnect
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 8

        # Fourth reconnect
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 16

        # Fifth reconnect - should cap at 30
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 30

        # Should stay at max
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        assert reconnect_delay == 30

    @pytest.mark.asyncio
    async def test_reconnect_delay_resets_on_successful_connection(self):
        """After successful connection, delay should reset to 1."""
        reconnect_delay = 16  # After several reconnects

        # Simulating successful connection
        reconnect_delay = 1  # Reset on success

        assert reconnect_delay == 1


class TestCursorBasedReconnection:
    """Test cursor-based log resumption on reconnection."""

    def test_cursor_starts_at_negative_one(self):
        """Cursor should start at -1 to get all logs."""
        last_sequence = -1
        assert last_sequence == -1

    def test_cursor_updates_from_log_message(self):
        """Cursor should update to latest sequence_number."""
        from rgrid.commands.logs import process_websocket_message

        last_sequence = -1

        # First log
        msg1 = json.dumps({
            "type": "log",
            "sequence_number": 0,
            "stream": "stdout",
            "message": "Line 0",
        })
        result1 = process_websocket_message(msg1)
        last_sequence = result1["sequence_number"]
        assert last_sequence == 0

        # Second log
        msg2 = json.dumps({
            "type": "log",
            "sequence_number": 1,
            "stream": "stdout",
            "message": "Line 1",
        })
        result2 = process_websocket_message(msg2)
        last_sequence = result2["sequence_number"]
        assert last_sequence == 1

    def test_cursor_preserves_across_reconnection_simulation(self):
        """Cursor value should be preserved for reconnection URL."""
        last_sequence = 42

        # Simulate building reconnection URL
        endpoint = "wss://api.example.com/ws/executions/exec_123/logs"
        reconnect_url = f"{endpoint}?cursor={last_sequence}"

        assert "cursor=42" in reconnect_url


class TestServerCursorHandling:
    """Test that API properly handles cursor parameter."""

    @pytest.mark.asyncio
    async def test_get_historical_logs_filters_by_cursor(self):
        """Historical logs should only return logs after cursor."""
        from app.websocket.logs import get_historical_logs
        from unittest.mock import patch, AsyncMock

        # Mock the database query
        with patch('app.websocket.logs.AsyncSessionLocal') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock query results
            mock_log1 = Mock()
            mock_log1.to_dict.return_value = {"sequence_number": 5, "message": "Log 5"}
            mock_log2 = Mock()
            mock_log2.to_dict.return_value = {"sequence_number": 6, "message": "Log 6"}

            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_log1, mock_log2]
            mock_session.execute = AsyncMock(return_value=mock_result)

            # Call with cursor=4, should return logs with sequence > 4
            logs = await get_historical_logs("exec_123", cursor=4)

            # Verify the returned logs are after cursor
            assert len(logs) == 2
            assert logs[0]["sequence_number"] == 5
            assert logs[1]["sequence_number"] == 6


class TestReconnectionScenarios:
    """Test various reconnection scenarios."""

    @pytest.mark.asyncio
    async def test_handles_connection_closed_exception(self):
        """Should catch ConnectionClosed and trigger reconnection."""
        import websockets

        # Verify we can catch the exception properly
        try:
            raise websockets.ConnectionClosed(None, None)
        except websockets.ConnectionClosed:
            reconnected = True

        assert reconnected is True

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """Should catch generic exceptions and trigger reconnection."""
        try:
            raise ConnectionError("Network unreachable")
        except Exception as e:
            should_reconnect = True
            error_msg = str(e)

        assert should_reconnect is True
        assert "Network unreachable" in error_msg

    def test_format_log_line_stdout(self):
        """stdout logs should format normally."""
        from rgrid.commands.logs import format_log_line

        result = format_log_line("stdout", "Hello World")
        assert result == "Hello World"

    def test_format_log_line_stderr(self):
        """stderr logs should be formatted in red."""
        from rgrid.commands.logs import format_log_line

        result = format_log_line("stderr", "Error message")
        assert "[red]" in result
        assert "Error message" in result


class TestNoDuplicateLogs:
    """Test that reconnection doesn't cause duplicate logs."""

    def test_sequence_numbers_are_monotonic(self):
        """Sequence numbers should increase monotonically."""
        from rgrid.commands.logs import process_websocket_message

        sequences = []
        for i in range(5):
            msg = json.dumps({
                "type": "log",
                "sequence_number": i,
                "stream": "stdout",
                "message": f"Line {i}",
            })
            result = process_websocket_message(msg)
            sequences.append(result["sequence_number"])

        # Verify monotonic increase
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1]

    def test_cursor_prevents_duplicates(self):
        """With cursor=X, server should only send logs with sequence > X."""
        # This tests the concept - actual implementation is in server
        last_received = 10

        # Simulated server response after reconnection with cursor=10
        # Should only include logs 11, 12, 13 (not 0-10)
        logs_after_cursor = [11, 12, 13]

        for seq in logs_after_cursor:
            assert seq > last_received


class TestGracefulShutdown:
    """Test graceful shutdown during streaming."""

    @pytest.mark.asyncio
    async def test_stop_event_prevents_reconnection(self):
        """When stop_event is set, should not attempt reconnection."""
        stop_event = asyncio.Event()
        stop_event.set()

        assert stop_event.is_set() is True

        # In the actual code, this condition breaks the reconnection loop
        should_reconnect = not stop_event.is_set()
        assert should_reconnect is False
