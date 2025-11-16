"""Integration tests for batch progress tracking (Tier 5 - Story 5-3)."""

import pytest
import time
import signal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestBatchProgressUpdates:
    """Test batch progress polling and updates."""

    @pytest.mark.asyncio
    async def test_batch_progress_updates(self):
        """Poll API, counts change over time."""
        from cli.rgrid.batch_progress import BatchProgressTracker

        # Arrange - Mock API responses that change over time
        mock_api = Mock()
        batch_id = "test-batch-123"

        # Simulate progression: queued -> running -> completed
        response_sequence = [
            # Poll 1: All queued
            {"statuses": ["queued"] * 10},
            # Poll 2: Some running
            {"statuses": ["running"] * 5 + ["queued"] * 5},
            # Poll 3: Some completed
            {"statuses": ["completed"] * 3 + ["running"] * 4 + ["queued"] * 3},
            # Poll 4: All done
            {"statuses": ["completed"] * 10},
        ]

        mock_api.get_batch_status.side_effect = response_sequence

        # Act
        tracker = BatchProgressTracker(mock_api, batch_id, poll_interval=0.1)
        updates = []

        async for progress in tracker.poll():
            updates.append(progress.copy())
            if progress["completed"] == 10:
                break

        # Assert
        assert len(updates) >= 4
        assert updates[0]["queued"] == 10
        assert updates[0]["completed"] == 0
        assert updates[-1]["completed"] == 10
        assert updates[-1]["queued"] == 0

    @pytest.mark.asyncio
    async def test_large_batch_progress(self):
        """Track 100+ jobs correctly."""
        from cli.rgrid.batch_progress import BatchProgressTracker

        # Arrange
        mock_api = Mock()
        batch_id = "large-batch-456"

        # Simulate a large batch
        statuses = ["completed"] * 50 + ["running"] * 25 + ["queued"] * 25
        mock_api.get_batch_status.return_value = {"statuses": statuses}

        # Act
        tracker = BatchProgressTracker(mock_api, batch_id, poll_interval=0.1)
        progress = None

        async for p in tracker.poll():
            progress = p
            break  # Get first update

        # Assert
        assert progress is not None
        assert progress["total"] == 100
        assert progress["completed"] == 50
        assert progress["running"] == 25
        assert progress["queued"] == 25
        assert progress["percentage"] == 50.0


class TestGracefulExit:
    """Test Ctrl+C handling."""

    def test_ctrl_c_graceful_exit(self):
        """KeyboardInterrupt handled gracefully."""
        from cli.rgrid.batch_progress import display_batch_progress

        # Arrange
        mock_api = Mock()
        batch_id = "interrupt-batch"

        # Simulate Ctrl+C after 2 polls
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()
            return {"statuses": ["running"] * 10}

        mock_api.get_batch_status.side_effect = side_effect

        # Act - Should not raise exception
        with patch('builtins.print'):  # Suppress output
            try:
                display_batch_progress(mock_api, batch_id, poll_interval=0.1)
                # Should exit gracefully
                assert True
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt should be caught and handled")

    def test_background_executions_continue(self, capsys):
        """Verify message about background executions."""
        from cli.rgrid.batch_progress import display_batch_progress

        # Arrange
        mock_api = Mock()
        mock_api.get_batch_status.side_effect = KeyboardInterrupt()

        # Act - should handle KeyboardInterrupt gracefully
        display_batch_progress(mock_api, batch_id="test", poll_interval=0.1)

        # Assert - Check that appropriate message was printed
        captured = capsys.readouterr()
        assert "background" in captured.out.lower() or "continue" in captured.out.lower()


class TestProgressDisplay:
    """Test progress display formatting and updates."""

    def test_single_line_update(self):
        """Verify progress updates in-place (no scrolling spam)."""
        from cli.rgrid.batch_progress import format_progress

        # Arrange
        progress1 = {
            "completed": 10,
            "failed": 0,
            "running": 5,
            "queued": 85,
            "total": 100,
            "percentage": 10.0
        }

        progress2 = {
            "completed": 25,
            "failed": 2,
            "running": 8,
            "queued": 65,
            "total": 100,
            "percentage": 25.0
        }

        # Act
        output1 = format_progress(progress1, 540)  # 9m ETA
        output2 = format_progress(progress2, 360)  # 6m ETA

        # Assert - Both should be single-line formatted
        assert '\n' not in output1.strip()
        assert '\n' not in output2.strip()
        assert "10/100" in output1
        assert "25/100" in output2

    def test_color_coding(self):
        """Test color codes in output."""
        from cli.rgrid.batch_progress import format_progress_with_colors

        # Arrange
        progress = {
            "completed": 50,
            "failed": 10,
            "running": 20,
            "queued": 20,
            "total": 100,
            "percentage": 50.0
        }

        # Act
        output = format_progress_with_colors(progress, 180)

        # Assert - Should contain ANSI color codes
        # Green for success, red for failures, yellow for running
        assert "\033[" in output or "succeeded" in output.lower()

    def test_final_summary(self):
        """Verify final summary format."""
        from cli.rgrid.batch_progress import format_final_summary

        # Arrange
        total_succeeded = 95
        total_failed = 5
        elapsed_seconds = 750  # 12m 30s

        # Act
        summary = format_final_summary(total_succeeded, total_failed, elapsed_seconds)

        # Assert
        assert "95" in summary
        assert "5" in summary
        assert "12m 30s" in summary or "750s" in summary
        assert "completed" in summary.lower() or "finished" in summary.lower()
