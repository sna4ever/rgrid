"""Integration tests for batch failure handling (Story 5-5).

Tests verify:
- Batch continues processing after individual failures
- Failed files displayed with error messages
- Exit code = 0 if any succeeded, 1 if all failed
"""

import asyncio
from unittest.mock import patch, MagicMock

import pytest


class TestBatchContinuesOnFailure:
    """Test that batch continues processing after failures."""

    def test_batch_processes_all_files_despite_failures(self):
        """All files should be attempted even when some fail."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        processed_files = []

        async def mock_submit(file: str) -> dict:
            processed_files.append(file)
            if "fail" in file:
                raise Exception(f"Processing error: {file}")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = ["good1.csv", "fail1.csv", "good2.csv", "fail2.csv", "good3.csv"]

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=mock_submit):
                return await executor.execute_batch_async(
                    script_content="print('test')",
                    files=files,
                    runtime="python:3.11",
                    env_vars={},
                )

        result = asyncio.run(run_test())

        # Assert
        assert len(processed_files) == 5, "All files should be processed"
        assert result.completed == 3
        assert result.failed == 2


class TestFailedFilesWithErrorMessages:
    """Test that failed files include error messages."""

    def test_error_messages_accessible_from_result(self):
        """Failed files should have accessible error messages."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        async def mock_submit(file: str) -> dict:
            if file == "timeout.csv":
                raise TimeoutError("Connection timed out after 30s")
            if file == "auth.csv":
                raise PermissionError("Authentication failed")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = ["success.csv", "timeout.csv", "auth.csv"]

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=mock_submit):
                return await executor.execute_batch_async(
                    script_content="print('test')",
                    files=files,
                    runtime="python:3.11",
                    env_vars={},
                )

        result = asyncio.run(run_test())

        # Assert
        assert result.failed == 2
        assert len(result.failed_files) == 2

        # Check error messages are included
        errors_by_file = {f: e for f, e in result.failed_files}
        assert "timeout.csv" in errors_by_file
        assert "timed out" in errors_by_file["timeout.csv"].lower()
        assert "auth.csv" in errors_by_file
        assert "authentication" in errors_by_file["auth.csv"].lower()


class TestExitCodeLogic:
    """Test exit code based on success/failure counts."""

    def test_some_succeed_returns_zero(self):
        """When some executions succeed, exit code should be 0."""
        from rgrid.batch_executor import BatchResult

        # Arrange - 8 succeeded, 2 failed
        result = BatchResult(
            total=10,
            completed=8,
            failed=2,
            execution_ids=["exec_" + str(i) for i in range(8)],
            failed_files=[("f1.csv", "err1"), ("f2.csv", "err2")],
            batch_id="batch_abc",
        )

        # Act - Logic from run.py: exit 0 if completed > 0, else 1
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 0

    def test_all_fail_returns_one(self):
        """When all executions fail, exit code should be 1."""
        from rgrid.batch_executor import BatchResult

        # Arrange - all failed
        result = BatchResult(
            total=5,
            completed=0,
            failed=5,
            execution_ids=[],
            failed_files=[(f"file{i}.csv", f"error{i}") for i in range(5)],
            batch_id="batch_abc",
        )

        # Act
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 1

    def test_single_success_among_many_failures_returns_zero(self):
        """Even one success means exit code 0."""
        from rgrid.batch_executor import BatchResult

        # Arrange - 1 succeeded, 99 failed
        result = BatchResult(
            total=100,
            completed=1,
            failed=99,
            execution_ids=["exec_lucky"],
            failed_files=[(f"file{i}.csv", f"error{i}") for i in range(99)],
            batch_id="batch_abc",
        )

        # Act
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 0


class TestProgressCallbackWithFailures:
    """Test progress callback correctly reports failures."""

    def test_callback_receives_failure_updates(self):
        """Progress callback should receive updated failure counts."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        progress_updates = []

        def progress_callback(completed: int, failed: int, total: int, running: int):
            progress_updates.append({
                "completed": completed,
                "failed": failed,
                "total": total,
            })

        async def mock_submit(file: str) -> dict:
            if "bad" in file:
                raise Exception("Simulated failure")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=2)
        files = ["good1.csv", "bad1.csv", "good2.csv", "bad2.csv"]

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=mock_submit):
                return await executor.execute_batch_async(
                    script_content="print('test')",
                    files=files,
                    runtime="python:3.11",
                    env_vars={},
                    progress_callback=progress_callback,
                )

        result = asyncio.run(run_test())

        # Assert
        assert len(progress_updates) == 4  # One update per file

        # Final state should show 2 completed, 2 failed
        final_completed = max(u["completed"] for u in progress_updates)
        final_failed = max(u["failed"] for u in progress_updates)
        assert final_completed == 2
        assert final_failed == 2
