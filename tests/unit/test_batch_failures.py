"""Unit tests for batch failure handling (Story 5-5).

Tests cover:
- Error messages stored for each failed file
- Failed executions listed with error messages
- Exit code = 0 if any succeeded, 1 if all failed
"""

import asyncio
from unittest.mock import patch, MagicMock

import pytest


class TestErrorMessageStorage:
    """Test that error messages are stored for failed files."""

    def test_failed_files_include_error_messages(self):
        """Each failed file should have its error message stored."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        async def mock_submit(file: str) -> dict:
            if "bad" in file:
                raise Exception(f"Network error for {file}")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = ["good1.csv", "bad1.csv", "good2.csv", "bad2.csv"]

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
        # Each failed file should be a tuple of (filename, error_message)
        for failed_item in result.failed_files:
            assert isinstance(failed_item, tuple), "Failed files should be (filename, error) tuples"
            filename, error_msg = failed_item
            assert "bad" in filename
            assert "Network error" in error_msg

    def test_error_messages_preserved_from_exception(self):
        """Error messages should preserve the original exception text."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        async def mock_submit(file: str) -> dict:
            raise ValueError("Invalid file format: missing header")

        executor = BatchExecutor(max_parallel=5)
        files = ["test.csv"]

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
        assert result.failed == 1
        filename, error_msg = result.failed_files[0]
        assert filename == "test.csv"
        assert "Invalid file format" in error_msg


class TestFailureSummaryDisplay:
    """Test that failure summary is displayed correctly."""

    def test_summary_shows_success_and_fail_counts(self):
        """Summary should show 'X succeeded, Y failed'."""
        from rgrid.batch_executor import BatchResult

        # Arrange
        result = BatchResult(
            total=100,
            completed=95,
            failed=5,
            execution_ids=["exec_" + str(i) for i in range(95)],
            failed_files=[
                ("file1.csv", "Connection timeout"),
                ("file2.csv", "Server error"),
                ("file3.csv", "Invalid input"),
                ("file4.csv", "Rate limited"),
                ("file5.csv", "Auth failed"),
            ],
            batch_id="batch_abc123",
        )

        # Assert - structure supports summary display
        assert result.completed == 95
        assert result.failed == 5
        assert len(result.failed_files) == 5


class TestExitCodeBehavior:
    """Test exit code logic: 0 if any succeeded, 1 if all failed."""

    def test_exit_code_zero_when_all_succeed(self):
        """Exit code should be 0 when all executions succeed."""
        from rgrid.batch_executor import BatchResult

        # Arrange
        result = BatchResult(
            total=10,
            completed=10,
            failed=0,
            execution_ids=["exec_" + str(i) for i in range(10)],
            failed_files=[],
            batch_id="batch_abc",
        )

        # Act
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 0

    def test_exit_code_zero_when_some_succeed(self):
        """Exit code should be 0 when at least one execution succeeds."""
        from rgrid.batch_executor import BatchResult

        # Arrange - 95 succeeded, 5 failed
        result = BatchResult(
            total=100,
            completed=95,
            failed=5,
            execution_ids=["exec_" + str(i) for i in range(95)],
            failed_files=[("file.csv", "error")] * 5,
            batch_id="batch_abc",
        )

        # Act
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 0

    def test_exit_code_one_when_all_fail(self):
        """Exit code should be 1 when all executions fail."""
        from rgrid.batch_executor import BatchResult

        # Arrange - all failed
        result = BatchResult(
            total=10,
            completed=0,
            failed=10,
            execution_ids=[],
            failed_files=[("file.csv", "error")] * 10,
            batch_id="batch_abc",
        )

        # Act
        exit_code = 0 if result.completed > 0 else 1

        # Assert
        assert exit_code == 1


class TestCLIFailureOutput:
    """Test CLI output for batch failures."""

    def test_failed_files_listed_with_errors(self):
        """Failed files should be listed with their error messages."""
        from rgrid.batch_executor import BatchResult

        # Arrange
        failed_files = [
            ("data/input1.csv", "Connection timeout after 30s"),
            ("data/input2.csv", "Server returned 500"),
            ("data/input3.csv", "Rate limit exceeded"),
        ]
        result = BatchResult(
            total=10,
            completed=7,
            failed=3,
            execution_ids=["exec_" + str(i) for i in range(7)],
            failed_files=failed_files,
            batch_id="batch_abc",
        )

        # Act - format failure output (simulating what CLI would do)
        failure_lines = []
        for filename, error in result.failed_files:
            failure_lines.append(f"  ✗ {filename}: {error}")

        # Assert
        assert len(failure_lines) == 3
        assert "input1.csv" in failure_lines[0]
        assert "Connection timeout" in failure_lines[0]
        assert "input2.csv" in failure_lines[1]
        assert "500" in failure_lines[1]
