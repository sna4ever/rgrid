"""Unit tests for execution metadata tracking (Story 8.6).

Tests for:
- duration_seconds: INT (calculated from completed_at - started_at)
- worker_hostname: VARCHAR(128) (hostname of the worker node)
- execution_metadata: JSONB (extensible metadata)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta


class TestExecutionMetadataFields:
    """Test that execution models have required metadata fields."""

    def test_api_execution_model_has_duration_seconds(self):
        """API Execution model should have duration_seconds field."""
        from api.app.models.execution import Execution

        # Check column exists
        assert hasattr(Execution, 'duration_seconds')

        # Check column properties
        column = Execution.__table__.columns.get('duration_seconds')
        assert column is not None
        assert column.nullable is True

    def test_api_execution_model_has_worker_hostname(self):
        """API Execution model should have worker_hostname field."""
        from api.app.models.execution import Execution

        # Check column exists
        assert hasattr(Execution, 'worker_hostname')

        # Check column properties
        column = Execution.__table__.columns.get('worker_hostname')
        assert column is not None
        assert column.nullable is True

    def test_api_execution_model_has_execution_metadata(self):
        """API Execution model should have execution_metadata JSONB field."""
        from api.app.models.execution import Execution

        # Check column exists
        assert hasattr(Execution, 'execution_metadata')

        # Check column properties
        column = Execution.__table__.columns.get('execution_metadata')
        assert column is not None
        assert column.nullable is True

    def test_runner_execution_model_has_duration_seconds(self):
        """Runner Execution model should have duration_seconds field."""
        from runner.runner.models import Execution

        # Check column exists
        assert hasattr(Execution, 'duration_seconds')

        column = Execution.__table__.columns.get('duration_seconds')
        assert column is not None

    def test_runner_execution_model_has_worker_hostname(self):
        """Runner Execution model should have worker_hostname field."""
        from runner.runner.models import Execution

        # Check column exists
        assert hasattr(Execution, 'worker_hostname')

        column = Execution.__table__.columns.get('worker_hostname')
        assert column is not None

    def test_runner_execution_model_has_execution_metadata(self):
        """Runner Execution model should have execution_metadata field."""
        from runner.runner.models import Execution

        # Check column exists
        assert hasattr(Execution, 'execution_metadata')

        column = Execution.__table__.columns.get('execution_metadata')
        assert column is not None


class TestExecutionResponseSchema:
    """Test that ExecutionResponse Pydantic schema has metadata fields."""

    def test_execution_response_has_duration_seconds(self):
        """ExecutionResponse should include duration_seconds field."""
        from rgrid_common.models import ExecutionResponse

        # Check field exists in model
        assert 'duration_seconds' in ExecutionResponse.model_fields

    def test_execution_response_has_worker_hostname(self):
        """ExecutionResponse should include worker_hostname field."""
        from rgrid_common.models import ExecutionResponse

        # Check field exists in model
        assert 'worker_hostname' in ExecutionResponse.model_fields

    def test_execution_response_has_execution_metadata(self):
        """ExecutionResponse should include execution_metadata field."""
        from rgrid_common.models import ExecutionResponse

        # Check field exists in model
        assert 'execution_metadata' in ExecutionResponse.model_fields

    def test_execution_response_can_serialize_with_metadata(self):
        """ExecutionResponse should serialize correctly with new metadata fields."""
        from rgrid_common.models import ExecutionResponse

        # Create response with all metadata fields
        response = ExecutionResponse(
            execution_id="exec_test123",
            script_content="print('hello')",
            runtime="python:3.11",
            status="completed",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=45,
            worker_hostname="worker-hetzner-01",
            execution_metadata={"python_version": "3.11.0", "env_vars_count": "3"},
        )

        # Verify fields are set
        assert response.duration_seconds == 45
        assert response.worker_hostname == "worker-hetzner-01"
        assert response.execution_metadata["python_version"] == "3.11.0"

    def test_execution_response_metadata_fields_are_optional(self):
        """New metadata fields should be optional (for backwards compatibility)."""
        from rgrid_common.models import ExecutionResponse

        # Create response WITHOUT new metadata fields
        response = ExecutionResponse(
            execution_id="exec_test123",
            script_content="print('hello')",
            runtime="python:3.11",
            status="queued",
            created_at=datetime.now(timezone.utc),
        )

        # Fields should default to None
        assert response.duration_seconds is None
        assert response.worker_hostname is None
        assert response.execution_metadata is None


class TestDurationSecondsCalculation:
    """Test duration_seconds is calculated correctly."""

    def test_duration_calculation_simple(self):
        """Duration should be calculated as completed_at - started_at."""
        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2025, 1, 15, 10, 1, 30, tzinfo=timezone.utc)  # 90 seconds later

        duration = int((completed - started).total_seconds())

        assert duration == 90

    def test_duration_calculation_subsecond(self):
        """Duration should handle subsecond precision (truncate to int)."""
        started = datetime(2025, 1, 15, 10, 0, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2025, 1, 15, 10, 0, 5, 500000, tzinfo=timezone.utc)  # 5.5 seconds

        duration = int((completed - started).total_seconds())

        assert duration == 5  # Truncated to int

    def test_duration_calculation_long_running(self):
        """Duration should handle long-running jobs (hours)."""
        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)  # 2.5+ hours later

        duration = int((completed - started).total_seconds())

        # 2 hours 30 minutes 45 seconds = 9045 seconds
        assert duration == 9045


class TestPollerMetadataUpdate:
    """Test that poller accepts and updates new metadata fields."""

    @pytest.mark.asyncio
    async def test_update_execution_result_accepts_duration_seconds(self):
        """update_execution_result should accept duration_seconds parameter."""
        from runner.runner.poller import JobPoller

        # Create mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Create poller
        poller = JobPoller(session_maker=Mock())

        # Call update_execution_result with duration_seconds
        await poller.update_execution_result(
            session=mock_session,
            execution_id="exec_test123",
            status="completed",
            exit_code=0,
            completed_at=datetime.utcnow(),
            duration_seconds=45,
        )

        # Verify execute was called (we'll check the values in integration tests)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_execution_result_accepts_worker_hostname(self):
        """update_execution_result should accept worker_hostname parameter."""
        from runner.runner.poller import JobPoller

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        poller = JobPoller(session_maker=Mock())

        # Call update_execution_result with worker_hostname
        await poller.update_execution_result(
            session=mock_session,
            execution_id="exec_test123",
            status="completed",
            exit_code=0,
            completed_at=datetime.utcnow(),
            worker_hostname="worker-hetzner-01",
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_execution_result_accepts_execution_metadata(self):
        """update_execution_result should accept execution_metadata parameter."""
        from runner.runner.poller import JobPoller

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        poller = JobPoller(session_maker=Mock())

        # Call update_execution_result with execution_metadata
        await poller.update_execution_result(
            session=mock_session,
            execution_id="exec_test123",
            status="completed",
            exit_code=0,
            completed_at=datetime.utcnow(),
            execution_metadata={"python_version": "3.11.0"},
        )

        mock_session.execute.assert_called_once()


class TestStatusCommandDisplaysMetadata:
    """Test that status command displays new metadata fields."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture
    def mock_api_response_with_metadata(self):
        """Mock API response with all metadata fields."""
        return {
            "execution_id": "exec_meta123",
            "status": "completed",
            "runtime": "python:3.11",
            "exit_code": 0,
            "created_at": "2025-01-15T10:00:00Z",
            "started_at": "2025-01-15T10:00:05Z",
            "completed_at": "2025-01-15T10:00:50Z",
            "duration_seconds": 45,
            "worker_hostname": "worker-hetzner-01",
            "execution_metadata": {"python_version": "3.11.0", "env_vars_count": 3},
            "stdout": "Hello World",
            "stderr": "",
            "output_truncated": False,
        }

    @patch('rgrid.commands.status.get_client')
    def test_status_displays_worker_hostname(self, mock_get_client, cli_runner, mock_api_response_with_metadata):
        """Status command should display worker_hostname when available."""
        from rgrid.commands.status import status

        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_with_metadata
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(status, ['exec_meta123'])

        assert result.exit_code == 0
        assert 'worker-hetzner-01' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_displays_duration_from_server(self, mock_get_client, cli_runner, mock_api_response_with_metadata):
        """Status command should use duration_seconds from server if available."""
        from rgrid.commands.status import status

        mock_client = Mock()
        mock_client.get_execution.return_value = mock_api_response_with_metadata
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(status, ['exec_meta123'])

        assert result.exit_code == 0
        # Duration should be displayed (45 seconds)
        assert 'Duration' in result.output
        assert '45' in result.output

    @patch('rgrid.commands.status.get_client')
    def test_status_handles_missing_worker_hostname(self, mock_get_client, cli_runner):
        """Status command should handle missing worker_hostname gracefully."""
        from rgrid.commands.status import status

        mock_response = {
            "execution_id": "exec_old123",
            "status": "completed",
            "runtime": "python:3.11",
            "exit_code": 0,
            "created_at": "2025-01-15T10:00:00Z",
            "started_at": "2025-01-15T10:00:05Z",
            "completed_at": "2025-01-15T10:00:50Z",
            # No worker_hostname (old execution)
            "stdout": "Hello",
            "stderr": "",
        }

        mock_client = Mock()
        mock_client.get_execution.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(status, ['exec_old123'])

        # Should not crash
        assert result.exit_code == 0
        # Worker field should not be displayed if not available
        assert 'Worker' not in result.output or 'worker-' not in result.output


class TestWorkerPopulatesMetadata:
    """Test that worker populates metadata fields on execution completion."""

    def test_worker_has_hostname_attribute(self):
        """Worker should have hostname attribute for tracking."""
        from runner.runner.worker import Worker

        # Create worker (won't actually connect to DB)
        with patch('runner.runner.worker.create_async_engine'):
            with patch('runner.runner.worker.async_sessionmaker'):
                with patch('runner.runner.worker.DockerExecutor'):
                    with patch('runner.runner.worker.HeartbeatManager'):
                        worker = Worker(
                            database_url="postgresql://test:test@localhost/test",
                            worker_id="test-worker-123",
                        )

        # Worker should have hostname set
        import socket
        assert worker.hostname == socket.gethostname()

    def test_worker_has_worker_id_attribute(self):
        """Worker should have worker_id attribute for tracking."""
        from runner.runner.worker import Worker

        with patch('runner.runner.worker.create_async_engine'):
            with patch('runner.runner.worker.async_sessionmaker'):
                with patch('runner.runner.worker.DockerExecutor'):
                    with patch('runner.runner.worker.HeartbeatManager'):
                        worker = Worker(
                            database_url="postgresql://test:test@localhost/test",
                            worker_id="custom-worker-id",
                        )

        assert worker.worker_id == "custom-worker-id"
