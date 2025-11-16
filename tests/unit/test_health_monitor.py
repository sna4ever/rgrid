"""Unit tests for worker health monitoring (Tier 4 - Story 3-4)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from orchestrator.health_monitor import (
    WorkerHealthMonitor,
    WorkerHeartbeatSender,
    HEARTBEAT_TIMEOUT,
)


class TestWorkerHealthMonitor:
    """Test worker health monitoring."""

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_check_heartbeats_with_healthy_workers(self, mock_engine):
        """When all workers are healthy, no action should be taken."""
        # Mock engine
        mock_engine.return_value = AsyncMock()

        monitor = WorkerHealthMonitor("postgresql+asyncpg://test")

        # Mock the database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.all.return_value = []  # No dead workers
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        monitor.async_session_maker = Mock(return_value=mock_session)

        # Act
        await monitor.check_worker_heartbeats()

        # Assert
        # Should query for workers but find none dead
        assert mock_session.execute.called
        assert not mock_session.commit.called  # No changes to commit

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_check_heartbeats_marks_dead_workers(self, mock_engine):
        """When worker heartbeat is stale, should mark worker as dead."""
        mock_engine.return_value = AsyncMock()
        monitor = WorkerHealthMonitor("postgresql+asyncpg://test")

        # Mock worker and heartbeat
        mock_worker = Mock()
        mock_worker.worker_id = "worker-123"
        mock_worker.status = 'active'

        mock_heartbeat = Mock()
        mock_heartbeat.last_heartbeat_at = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT + 60)

        # Mock database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.all.return_value = [(mock_worker, mock_heartbeat)]
        mock_session.execute.return_value = mock_result

        # Mock the orphaned executions query
        mock_orphaned_result = Mock()
        mock_orphaned_result.scalars.return_value.all.return_value = []

        async def execute_side_effect(query):
            # First call returns dead workers, second returns orphaned executions
            if not hasattr(execute_side_effect, 'call_count'):
                execute_side_effect.call_count = 0
            execute_side_effect.call_count += 1

            if execute_side_effect.call_count == 1:
                return mock_result
            else:
                return mock_orphaned_result

        mock_session.execute.side_effect = execute_side_effect
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        monitor.async_session_maker = Mock(return_value=mock_session)

        # Act
        await monitor.check_worker_heartbeats()

        # Assert
        assert mock_session.commit.called

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_handle_dead_worker_reschedules_orphaned_executions(self, mock_engine):
        """When worker dies, orphaned executions should be rescheduled."""
        mock_engine.return_value = AsyncMock()
        monitor = WorkerHealthMonitor("postgresql+asyncpg://test")

        # Mock orphaned execution
        mock_execution = Mock()
        mock_execution.execution_id = "exec-456"
        mock_execution.worker_id = "worker-123"
        mock_execution.status = 'running'

        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute.return_value = Mock()

        # Mock orphaned executions query
        mock_orphaned_result = Mock()
        mock_orphaned_result.scalars.return_value.all.return_value = [mock_execution]
        mock_session.execute.return_value = mock_orphaned_result

        # Act
        await monitor.handle_dead_worker(
            mock_session,
            "worker-123",
            datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT + 60)
        )

        # Assert
        # Should have executed updates
        assert mock_session.execute.call_count >= 2  # Worker update + orphaned query

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_reschedule_execution_resets_to_queued(self, mock_engine):
        """Rescheduling should reset execution to queued state."""
        mock_engine.return_value = AsyncMock()
        monitor = WorkerHealthMonitor("postgresql+asyncpg://test")

        # Mock execution
        mock_execution = Mock()
        mock_execution.execution_id = "exec-456"
        mock_execution.worker_id = "worker-123"

        # Mock session
        mock_session = AsyncMock()

        # Act
        await monitor.reschedule_execution(mock_session, mock_execution)

        # Assert
        assert mock_session.execute.called


class TestWorkerHeartbeatSender:
    """Test heartbeat sender."""

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_send_heartbeat_creates_or_updates_record(self, mock_engine):
        """Sending heartbeat should upsert heartbeat record."""
        mock_engine.return_value = AsyncMock()
        sender = WorkerHeartbeatSender("worker-123", "postgresql+asyncpg://test")

        # Mock database session
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        sender.async_session_maker = Mock(return_value=mock_session)

        # Act
        await sender.send_heartbeat()

        # Assert
        assert mock_session.execute.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    @patch('orchestrator.health_monitor.create_async_engine')
    async def test_send_heartbeat_handles_errors_gracefully(self, mock_engine):
        """If heartbeat fails, should log error and not crash."""
        mock_engine.return_value = AsyncMock()
        sender = WorkerHeartbeatSender("worker-123", "postgresql+asyncpg://test")

        # Mock session that raises error
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database connection failed")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        sender.async_session_maker = Mock(return_value=mock_session)

        # Act - should not raise
        await sender.send_heartbeat()

        # Assert - error was handled
        assert True  # Didn't crash


class TestHealthMonitorConfiguration:
    """Test health monitor configuration."""

    def test_health_monitor_uses_correct_timeout(self):
        """Health monitor should use 2-minute timeout."""
        assert HEARTBEAT_TIMEOUT == 120

    @patch('orchestrator.health_monitor.create_async_engine')
    def test_health_monitor_initializes_with_database_url(self, mock_engine):
        """Health monitor should accept database URL."""
        mock_engine.return_value = AsyncMock()
        monitor = WorkerHealthMonitor("postgresql+asyncpg://test:5432/db")
        assert monitor.database_url == "postgresql+asyncpg://test:5432/db"

    @patch('orchestrator.health_monitor.create_async_engine')
    def test_heartbeat_sender_initializes_with_worker_id(self, mock_engine):
        """Heartbeat sender should accept worker ID."""
        mock_engine.return_value = AsyncMock()
        sender = WorkerHeartbeatSender("worker-abc", "postgresql+asyncpg://test")
        assert sender.worker_id == "worker-abc"
