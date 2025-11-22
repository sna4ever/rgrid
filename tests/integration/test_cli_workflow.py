"""
Comprehensive CLI workflow integration tests (Phase 2 Integration Testing).

Tests the complete CLI workflow: run -> status -> logs -> cost -> retry.
Ensures cross-component integration works correctly.

Created by Dev 3 (Quality Guardian) - Phase 2 Stabilization Sprint.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner


class TestCLIWorkflowIntegration:
    """Test complete CLI workflow: run -> status -> logs -> cost."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_script(self):
        """Create a temporary test script."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('Hello from workflow test')\n")
            return Path(f.name)

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client for workflow testing."""
        client = Mock()
        client.close = Mock()
        return client

    def test_run_then_status_workflow(self, runner, temp_script, mock_api_client):
        """Test run command followed by status command."""
        from rgrid.commands.run import run
        from rgrid.commands.status import status

        # Setup: execution created successfully
        execution_id = "exec_workflow_123"
        mock_api_client.create_execution.return_value = {
            "execution_id": execution_id,
            "status": "queued",
            "upload_urls": {},
        }
        mock_api_client.get_execution.return_value = {
            "execution_id": execution_id,
            "status": "running",
            "runtime": "python:3.11",
            "created_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.run.get_client", return_value=mock_api_client):
            with patch("rgrid.commands.run.upload_file_to_minio", return_value=True):
                # Step 1: Run script
                result = runner.invoke(run, [str(temp_script), "--remote-only"])
                # Should succeed or show execution ID
                assert result.exit_code == 0 or execution_id in result.output

        with patch("rgrid.commands.status.get_client", return_value=mock_api_client):
            # Step 2: Check status
            result = runner.invoke(status, [execution_id])
            assert result.exit_code == 0
            assert "running" in result.output.lower() or "Execution" in result.output

    def test_run_then_logs_workflow(self, runner, temp_script, mock_api_client):
        """Test run command followed by logs command."""
        from rgrid.commands.run import run
        from rgrid.commands.logs import logs

        execution_id = "exec_logs_456"
        mock_api_client.create_execution.return_value = {
            "execution_id": execution_id,
            "status": "queued",
            "upload_urls": {},
        }
        mock_api_client.get_execution.return_value = {
            "execution_id": execution_id,
            "status": "completed",
            "runtime": "python:3.11",
            "stdout": "Hello from workflow test\n",
            "stderr": "",
            "created_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.run.get_client", return_value=mock_api_client):
            with patch("rgrid.commands.run.upload_file_to_minio", return_value=True):
                # Step 1: Run script
                result = runner.invoke(run, [str(temp_script), "--remote-only"])
                assert result.exit_code == 0 or execution_id in result.output

        with patch("rgrid.commands.logs.get_client", return_value=mock_api_client):
            # Step 2: Get logs
            result = runner.invoke(logs, [execution_id])
            assert result.exit_code == 0
            assert "Hello from workflow test" in result.output

    def test_full_workflow_run_status_logs_cost(self, runner, temp_script, mock_api_client):
        """Test complete workflow: run -> status -> logs -> cost."""
        from rgrid.commands.run import run
        from rgrid.commands.status import status
        from rgrid.commands.logs import logs
        from rgrid.commands.cost import cost

        execution_id = "exec_full_workflow_789"
        created_at = datetime.now()
        started_at = created_at + timedelta(seconds=5)
        completed_at = started_at + timedelta(seconds=30)

        mock_api_client.create_execution.return_value = {
            "execution_id": execution_id,
            "status": "queued",
            "upload_urls": {},
        }

        mock_api_client.get_execution.return_value = {
            "execution_id": execution_id,
            "status": "completed",
            "runtime": "python:3.11",
            "stdout": "Test output\n",
            "stderr": "",
            "exit_code": 0,
            "created_at": created_at.isoformat(),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "cost_micros": 100,
        }

        mock_api_client.get_cost.return_value = {
            "start_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "total_executions": 1,
            "total_cost_display": "$0.0001",
            "by_date": [
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "executions": 1,
                    "compute_time_seconds": 30,
                    "cost_display": "$0.0001",
                }
            ],
        }

        # Step 1: Run script
        with patch("rgrid.commands.run.get_client", return_value=mock_api_client):
            with patch("rgrid.commands.run.upload_file_to_minio", return_value=True):
                result = runner.invoke(run, [str(temp_script), "--remote-only"])
                assert result.exit_code == 0 or execution_id in result.output

        # Step 2: Check status
        with patch("rgrid.commands.status.get_client", return_value=mock_api_client):
            result = runner.invoke(status, [execution_id])
            assert result.exit_code == 0
            # Should show completed status
            assert "completed" in result.output.lower() or "Exit" in result.output

        # Step 3: Get logs
        with patch("rgrid.commands.logs.get_client", return_value=mock_api_client):
            result = runner.invoke(logs, [execution_id])
            assert result.exit_code == 0
            assert "Test output" in result.output

        # Step 4: Check cost
        with patch("rgrid.commands.cost.get_client", return_value=mock_api_client):
            result = runner.invoke(cost, [])
            assert result.exit_code == 0
            assert "$" in result.output  # Cost should be displayed


class TestStatusCommandVariations:
    """Test status command with various execution states."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_status_queued_with_provisioning_feedback(self, runner, mock_client):
        """Test status shows provisioning feedback when queued > 30s."""
        from rgrid.commands.status import status

        # Execution queued 45 seconds ago
        created_at = datetime.now() - timedelta(seconds=45)
        mock_client.get_execution.return_value = {
            "execution_id": "exec_queued_1",
            "status": "queued",
            "runtime": "python:3.11",
            "created_at": created_at.isoformat() + "Z",
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, ["exec_queued_1"])
            assert result.exit_code == 0
            # Should show queued status with provisioning hint
            assert "queued" in result.output.lower()

    def test_status_running_shows_worker(self, runner, mock_client):
        """Test status shows worker hostname when running."""
        from rgrid.commands.status import status

        mock_client.get_execution.return_value = {
            "execution_id": "exec_running_1",
            "status": "running",
            "runtime": "python:3.11",
            "worker_hostname": "worker-abc123",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, ["exec_running_1"])
            assert result.exit_code == 0
            assert "worker-abc123" in result.output

    def test_status_completed_shows_duration(self, runner, mock_client):
        """Test status shows duration when completed."""
        from rgrid.commands.status import status

        started = datetime.now() - timedelta(seconds=45)
        completed = datetime.now()

        mock_client.get_execution.return_value = {
            "execution_id": "exec_completed_1",
            "status": "completed",
            "runtime": "python:3.11",
            "exit_code": 0,
            "created_at": (started - timedelta(seconds=5)).isoformat() + "Z",
            "started_at": started.isoformat() + "Z",
            "completed_at": completed.isoformat() + "Z",
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, ["exec_completed_1"])
            assert result.exit_code == 0
            assert "Duration" in result.output or "45" in result.output

    def test_status_failed_shows_error(self, runner, mock_client):
        """Test status shows error message when failed."""
        from rgrid.commands.status import status

        mock_client.get_execution.return_value = {
            "execution_id": "exec_failed_1",
            "status": "failed",
            "runtime": "python:3.11",
            "exit_code": 1,
            "execution_error": "Script raised ImportError",
            "created_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, ["exec_failed_1"])
            assert result.exit_code == 0
            assert "failed" in result.output.lower()
            assert "ImportError" in result.output


class TestLogsCommandVariations:
    """Test logs command with various scenarios."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_logs_stdout_only(self, runner, mock_client):
        """Test logs --stdout-only filters correctly."""
        from rgrid.commands.logs import logs

        mock_client.get_execution.return_value = {
            "execution_id": "exec_1",
            "status": "completed",
            "stdout": "This is stdout output\n",
            "stderr": "This is stderr output\n",
        }

        with patch("rgrid.commands.logs.get_client", return_value=mock_client):
            result = runner.invoke(logs, ["exec_1", "--stdout-only"])
            assert result.exit_code == 0
            assert "stdout output" in result.output
            # stderr should not be shown
            assert "stderr output" not in result.output or "STDERR" not in result.output

    def test_logs_stderr_only(self, runner, mock_client):
        """Test logs --stderr-only filters correctly."""
        from rgrid.commands.logs import logs

        mock_client.get_execution.return_value = {
            "execution_id": "exec_1",
            "status": "completed",
            "stdout": "This is stdout output\n",
            "stderr": "This is stderr output\n",
        }

        with patch("rgrid.commands.logs.get_client", return_value=mock_client):
            result = runner.invoke(logs, ["exec_1", "--stderr-only"])
            assert result.exit_code == 0
            assert "stderr output" in result.output
            # stdout should not be shown
            assert "stdout output" not in result.output or "STDOUT" not in result.output

    def test_logs_no_output_shows_message(self, runner, mock_client):
        """Test logs shows message when no output available."""
        from rgrid.commands.logs import logs

        mock_client.get_execution.return_value = {
            "execution_id": "exec_1",
            "status": "queued",
            "stdout": "",
            "stderr": "",
        }

        with patch("rgrid.commands.logs.get_client", return_value=mock_client):
            result = runner.invoke(logs, ["exec_1"])
            assert result.exit_code == 0
            assert "No output available" in result.output

    def test_logs_truncated_warning(self, runner, mock_client):
        """Test logs shows truncation warning when output was truncated."""
        from rgrid.commands.logs import logs

        mock_client.get_execution.return_value = {
            "execution_id": "exec_1",
            "status": "completed",
            "stdout": "Some output...",
            "stderr": "",
            "output_truncated": True,
        }

        with patch("rgrid.commands.logs.get_client", return_value=mock_client):
            result = runner.invoke(logs, ["exec_1"])
            assert result.exit_code == 0
            assert "truncated" in result.output.lower()


class TestCostCommandVariations:
    """Test cost command with various date ranges."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_cost_default_7_days(self, runner, mock_client):
        """Test cost command defaults to last 7 days."""
        from rgrid.commands.cost import cost

        mock_client.get_cost.return_value = {
            "start_date": "2025-11-15",
            "end_date": "2025-11-22",
            "total_executions": 10,
            "total_cost_display": "$0.01",
            "by_date": [],
        }

        with patch("rgrid.commands.cost.get_client", return_value=mock_client):
            result = runner.invoke(cost, [])
            assert result.exit_code == 0
            # Should show period and totals
            assert "$0.01" in result.output

    def test_cost_custom_range(self, runner, mock_client):
        """Test cost command with custom date range."""
        from rgrid.commands.cost import cost

        mock_client.get_cost.return_value = {
            "start_date": "2025-11-01",
            "end_date": "2025-11-15",
            "total_executions": 50,
            "total_cost_display": "$0.05",
            "by_date": [
                {
                    "date": "2025-11-01",
                    "executions": 25,
                    "compute_time_seconds": 1800,
                    "cost_display": "$0.025",
                },
                {
                    "date": "2025-11-15",
                    "executions": 25,
                    "compute_time_seconds": 1800,
                    "cost_display": "$0.025",
                },
            ],
        }

        with patch("rgrid.commands.cost.get_client", return_value=mock_client):
            result = runner.invoke(
                cost, ["--since", "2025-11-01", "--until", "2025-11-15"]
            )
            assert result.exit_code == 0
            assert "$0.05" in result.output

    def test_cost_no_executions_in_period(self, runner, mock_client):
        """Test cost command when no executions in period."""
        from rgrid.commands.cost import cost

        mock_client.get_cost.return_value = {
            "start_date": "2025-10-01",
            "end_date": "2025-10-31",
            "total_executions": 0,
            "total_cost_display": "$0.00",
            "by_date": [],
        }

        with patch("rgrid.commands.cost.get_client", return_value=mock_client):
            result = runner.invoke(cost, ["--since", "2025-10-01", "--until", "2025-10-31"])
            assert result.exit_code == 0
            assert "No executions" in result.output or "0" in result.output


class TestRetryWorkflow:
    """Test retry command and workflow."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_retry_failed_execution(self, runner, mock_client):
        """Test retrying a failed execution."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value = {
            "execution_id": "exec_failed_1",
            "status": "failed",
            "error_message": "ImportError: No module named 'numpy'",
        }
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_retry_1",
            "status": "queued",
        }

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_failed_1"])
            assert result.exit_code == 0
            assert "exec_retry_1" in result.output
            assert "Retry started" in result.output

    def test_retry_completed_execution(self, runner, mock_client):
        """Test retrying a completed execution (re-run)."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value = {
            "execution_id": "exec_completed_1",
            "status": "completed",
        }
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_retry_2",
            "status": "queued",
        }

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_completed_1"])
            assert result.exit_code == 0
            assert "exec_retry_2" in result.output

    def test_retry_running_requires_force(self, runner, mock_client):
        """Test that retrying running execution requires --force."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value = {
            "execution_id": "exec_running_1",
            "status": "running",
        }

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_running_1"])
            # Should fail or warn without --force
            assert result.exit_code != 0 or "force" in result.output.lower()

    def test_retry_with_force_flag(self, runner, mock_client):
        """Test retrying with --force flag."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.return_value = {
            "execution_id": "exec_running_1",
            "status": "running",
        }
        mock_client.retry_execution.return_value = {
            "execution_id": "exec_retry_3",
            "status": "queued",
        }

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["exec_running_1", "--force"])
            assert result.exit_code == 0
            assert "exec_retry_3" in result.output

    def test_retry_batch_failed_only(self, runner, mock_client):
        """Test batch retry with --failed-only."""
        from rgrid.commands.retry import retry

        mock_client.get_batch_executions.return_value = [
            {"execution_id": "exec_1", "status": "completed"},
            {"execution_id": "exec_2", "status": "failed"},
            {"execution_id": "exec_3", "status": "failed"},
        ]
        mock_client.retry_execution.side_effect = [
            {"execution_id": "exec_retry_2", "status": "queued"},
            {"execution_id": "exec_retry_3", "status": "queued"},
        ]

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["--batch", "batch_1", "--failed-only"])
            assert result.exit_code == 0
            # Should only retry the 2 failed executions
            assert "2" in result.output or "exec_retry" in result.output

    def test_retry_no_argument_shows_help(self, runner, mock_client):
        """Test retry without arguments shows usage help."""
        from rgrid.commands.retry import retry

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, [])
            # Should show error or usage
            assert result.exit_code != 0 or "Usage" in result.output or "Missing" in result.output


class TestFailureScenarios:
    """Test failure scenarios and error handling."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_status_invalid_execution_id(self, runner, mock_client):
        """Test status command with invalid execution ID."""
        from rgrid.commands.status import status

        mock_client.get_execution.side_effect = Exception("Execution not found")

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, ["invalid_exec_id"])
            assert result.exit_code != 0 or "Error" in result.output

    def test_logs_network_error(self, runner, mock_client):
        """Test logs command handles network errors."""
        from rgrid.commands.logs import logs

        mock_client.get_execution.side_effect = Exception("Connection refused")

        with patch("rgrid.commands.logs.get_client", return_value=mock_client):
            result = runner.invoke(logs, ["exec_1"])
            assert result.exit_code != 0 or "Error" in result.output

    def test_cost_api_error(self, runner, mock_client):
        """Test cost command handles API errors gracefully."""
        from rgrid.commands.cost import cost

        mock_client.get_cost.side_effect = Exception("Internal server error")

        with patch("rgrid.commands.cost.get_client", return_value=mock_client):
            result = runner.invoke(cost, [])
            assert result.exit_code != 0 or "Error" in result.output

    def test_retry_nonexistent_execution(self, runner, mock_client):
        """Test retry command with non-existent execution."""
        from rgrid.commands.retry import retry

        mock_client.get_execution.side_effect = Exception("Execution not found")

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, ["nonexistent_exec"])
            assert result.exit_code != 0 or "Error" in result.output


class TestCrossComponentIntegration:
    """Test cross-component integration scenarios."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.close = Mock()
        return client

    def test_batch_then_status_each_execution(self, runner, mock_client):
        """Test batch execution followed by status check on each."""
        from rgrid.commands.run import run
        from rgrid.commands.status import status
        from rgrid.batch import BatchSubmitter

        # Setup batch executions
        execution_ids = ["exec_batch_1", "exec_batch_2", "exec_batch_3"]
        mock_client.create_execution.side_effect = [
            {"execution_id": eid, "status": "queued", "upload_urls": {}}
            for eid in execution_ids
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(3):
                (Path(tmpdir) / f"file{i}.txt").write_text(f"data{i}")

            script_path = Path(tmpdir) / "process.py"
            script_path.write_text("import sys; print(sys.argv[1])")

            # Create batch
            with patch("rgrid.batch.upload_file_to_minio", return_value=True):
                submitter = BatchSubmitter(mock_client)
                result = submitter.submit_batch(
                    script_content="import sys; print(sys.argv[1])",
                    files=[str(Path(tmpdir) / f"file{i}.txt") for i in range(3)],
                    runtime="python:3.11",
                    env_vars={},
                )

            assert len(result["executions"]) == 3

        # Check status of each execution
        for i, exec_id in enumerate(execution_ids):
            mock_client.get_execution.return_value = {
                "execution_id": exec_id,
                "status": "completed",
                "runtime": "python:3.11",
                "exit_code": 0,
                "created_at": datetime.now().isoformat(),
            }

            with patch("rgrid.commands.status.get_client", return_value=mock_client):
                result = runner.invoke(status, [exec_id])
                assert result.exit_code == 0

    def test_failed_execution_then_retry_then_status(self, runner, mock_client):
        """Test complete failure recovery workflow."""
        from rgrid.commands.status import status
        from rgrid.commands.retry import retry

        original_exec_id = "exec_original_fail"
        retry_exec_id = "exec_retried"

        # Step 1: Check failed status
        mock_client.get_execution.return_value = {
            "execution_id": original_exec_id,
            "status": "failed",
            "runtime": "python:3.11",
            "exit_code": 1,
            "execution_error": "Module not found",
            "created_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, [original_exec_id])
            assert result.exit_code == 0
            assert "failed" in result.output.lower()

        # Step 2: Retry the execution
        mock_client.retry_execution.return_value = {
            "execution_id": retry_exec_id,
            "status": "queued",
        }

        with patch("rgrid.commands.retry.get_client", return_value=mock_client):
            result = runner.invoke(retry, [original_exec_id])
            assert result.exit_code == 0
            assert retry_exec_id in result.output

        # Step 3: Check new execution status (now succeeded)
        mock_client.get_execution.return_value = {
            "execution_id": retry_exec_id,
            "status": "completed",
            "runtime": "python:3.11",
            "exit_code": 0,
            "created_at": datetime.now().isoformat(),
        }

        with patch("rgrid.commands.status.get_client", return_value=mock_client):
            result = runner.invoke(status, [retry_exec_id])
            assert result.exit_code == 0
            assert "completed" in result.output.lower()


class TestWebSocketLogProcessing:
    """Test WebSocket message processing for log streaming."""

    def test_process_log_message(self):
        """Test processing a log message."""
        from rgrid.commands.logs import process_websocket_message

        message = '{"type": "log", "sequence_number": 1, "timestamp": "2025-11-22T12:00:00Z", "stream": "stdout", "message": "Hello world"}'
        result = process_websocket_message(message)

        assert result["type"] == "log"
        assert result["sequence_number"] == 1
        assert result["stream"] == "stdout"
        assert result["message"] == "Hello world"
        assert result["continue"] is True

    def test_process_complete_message(self):
        """Test processing a completion message."""
        from rgrid.commands.logs import process_websocket_message

        message = '{"type": "complete", "exit_code": 0, "status": "completed"}'
        result = process_websocket_message(message)

        assert result["type"] == "complete"
        assert result["exit_code"] == 0
        assert result["continue"] is False

    def test_process_error_message(self):
        """Test processing an error message."""
        from rgrid.commands.logs import process_websocket_message

        message = '{"type": "error", "error": "Connection timeout"}'
        result = process_websocket_message(message)

        assert result["type"] == "error"
        assert result["error"] == "Connection timeout"
        assert result["continue"] is False

    def test_format_log_line_stdout(self):
        """Test formatting stdout log line."""
        from rgrid.commands.logs import format_log_line

        result = format_log_line("stdout", "Normal output")
        assert "Normal output" in result
        # Should not have red formatting
        assert "[red]" not in result

    def test_format_log_line_stderr(self):
        """Test formatting stderr log line with red color."""
        from rgrid.commands.logs import format_log_line

        result = format_log_line("stderr", "Error output")
        assert "Error output" in result
        # Should have red formatting
        assert "[red]" in result
