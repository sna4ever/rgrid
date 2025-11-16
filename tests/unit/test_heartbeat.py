"""
Unit tests for heartbeat functionality (Story NEW-7).

Tests the heartbeat mechanism that detects dead workers.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from runner.runner.heartbeat import HeartbeatManager, DeadWorkerCleaner


class TestHeartbeatManager:
    """Test the worker heartbeat manager."""

    @pytest.mark.asyncio
    async def test_heartbeat_upsert_creates_new_record(self):
        """When no heartbeat exists, should create new record in database."""
        # Arrange
        worker_id = "test-worker-123"
        hostname = "test-host"
        mock_session = AsyncMock(spec=AsyncSession)

        manager = HeartbeatManager(worker_id, hostname)

        # Act
        await manager.send_heartbeat(mock_session)

        # Assert
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql = str(call_args.args[0])
        assert "worker_heartbeats" in sql.lower()
        assert call_args.args[1]["worker_id"] == worker_id

    @pytest.mark.asyncio
    async def test_heartbeat_upsert_updates_existing_record(self):
        """When heartbeat exists, should update last_heartbeat_at timestamp."""
        # Arrange
        worker_id = "test-worker-456"
        hostname = "test-host"
        mock_session = AsyncMock(spec=AsyncSession)
        manager = HeartbeatManager(worker_id, hostname)

        # Act - send heartbeat twice
        await manager.send_heartbeat(mock_session)
        await manager.send_heartbeat(mock_session)

        # Assert - should have been called twice (upsert pattern)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_heartbeat_with_db_failure_logs_error_and_continues(self):
        """When database fails, heartbeat should log error but not crash."""
        # Arrange
        worker_id = "test-worker-789"
        hostname = "test-host"
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database connection lost")

        manager = HeartbeatManager(worker_id, hostname)

        # Act - should not raise exception
        try:
            await manager.send_heartbeat(mock_session)
            exception_raised = False
        except Exception:
            exception_raised = True

        # Assert - should catch and log error, not propagate
        assert not exception_raised

    @pytest.mark.asyncio
    async def test_heartbeat_loop_runs_periodically(self):
        """Heartbeat loop should send heartbeat every 30 seconds."""
        # Arrange
        worker_id = "test-worker-loop"
        hostname = "test-host"
        mock_session_factory = MagicMock()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        manager = HeartbeatManager(worker_id, hostname, interval=0.1)

        # Act - run loop for short time
        loop_task = asyncio.create_task(manager.start_heartbeat_loop(mock_session_factory))
        await asyncio.sleep(0.35)
        manager.stop_heartbeat_loop()
        await loop_task

        # Assert - should have sent multiple heartbeats
        assert mock_session.execute.call_count >= 2


class TestDeadWorkerCleaner:
    """Test the dead worker detection and cleanup daemon."""

    @pytest.mark.asyncio
    async def test_find_stale_workers_returns_workers_with_old_heartbeat(self):
        """Should find workers with heartbeat older than threshold (2 minutes)."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[
            MagicMock(worker_id="dead-worker-1"),
            MagicMock(worker_id="dead-worker-2"),
        ])
        mock_session.execute = AsyncMock(return_value=mock_result)

        cleaner = DeadWorkerCleaner(stale_threshold_minutes=2)

        # Act
        stale_workers = await cleaner.find_stale_workers(mock_session)

        # Assert
        assert len(stale_workers) == 2
        assert stale_workers[0].worker_id == "dead-worker-1"
        assert stale_workers[1].worker_id == "dead-worker-2"

    @pytest.mark.asyncio
    async def test_mark_jobs_failed_updates_running_executions(self):
        """Should mark all running jobs from dead worker as failed."""
        # Arrange
        worker_id = "dead-worker-123"
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        cleaner = DeadWorkerCleaner()

        # Act
        jobs_failed = await cleaner.mark_jobs_failed(mock_session, worker_id)

        # Assert
        assert jobs_failed == 3
        call_args = mock_session.execute.call_args
        sql = str(call_args.args[0])
        assert "executions" in sql.lower()
        assert call_args.args[1]["worker_id"] == worker_id

    @pytest.mark.asyncio
    async def test_cleanup_daemon_loop_runs_periodically(self):
        """Cleanup daemon should run every 60 seconds."""
        # Arrange
        mock_session_factory = MagicMock()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        cleaner = DeadWorkerCleaner(check_interval=0.1)

        # Act - run loop for short time
        loop_task = asyncio.create_task(cleaner.start_cleanup_loop(mock_session_factory))
        await asyncio.sleep(0.35)
        cleaner.stop_cleanup_loop()
        await loop_task

        # Assert - should have checked multiple times
        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_cleanup_with_db_failure_logs_error_and_continues(self):
        """When database fails during cleanup, should log error but continue running."""
        # Arrange
        mock_session_factory = MagicMock()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database error")
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        cleaner = DeadWorkerCleaner(check_interval=0.1)

        # Act - should not crash
        loop_task = asyncio.create_task(cleaner.start_cleanup_loop(mock_session_factory))
        await asyncio.sleep(0.15)
        cleaner.stop_cleanup_loop()

        try:
            await loop_task
            exception_raised = False
        except Exception:
            exception_raised = True

        # Assert - should handle errors gracefully
        assert not exception_raised
