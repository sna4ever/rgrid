"""Unit tests for batch parallel execution (Story 5-2).

Tests cover:
- Default parallelism of 10
- Custom parallelism via --parallel flag
- Semaphore-based concurrency limiting
- Progress display with running/completed/failed counts
- Graceful handling of partial failures
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest


class TestDefaultParallelism:
    """Test that default parallelism is 10 when flag omitted."""

    def test_default_parallelism_is_10(self):
        """When --parallel flag omitted, default should be 10."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange & Act
        executor = BatchExecutor()

        # Assert
        assert executor.max_parallel == 10

    def test_parallel_flag_sets_limit(self):
        """When --parallel N provided, should set limit to N."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange & Act
        executor = BatchExecutor(max_parallel=20)

        # Assert
        assert executor.max_parallel == 20

    def test_parallel_value_1_allows_sequential(self):
        """When --parallel 1, should allow sequential execution."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange & Act
        executor = BatchExecutor(max_parallel=1)

        # Assert
        assert executor.max_parallel == 1


class TestConcurrencyLimiting:
    """Test semaphore-based concurrency limiting."""

    def test_semaphore_limits_concurrent_submissions(self):
        """Executor should never exceed max_parallel concurrent tasks."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def slow_submit(file: str) -> dict:
            nonlocal max_concurrent_observed, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent_observed:
                    max_concurrent_observed = current_concurrent
            await asyncio.sleep(0.05)  # Simulate network delay
            async with lock:
                current_concurrent -= 1
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=3)
        files = [f"file{i}.csv" for i in range(10)]

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=slow_submit):
                await executor.execute_batch_async(
                    script_content="print('test')",
                    files=files,
                    runtime="python:3.11",
                    env_vars={},
                )
            return max_concurrent_observed

        result = asyncio.run(run_test())

        # Assert
        assert result <= 3, f"Max concurrent was {result}, should be <= 3"

    def test_all_files_processed_despite_limit(self):
        """All files should be processed even with low parallelism."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        processed_files = []

        async def mock_submit(file: str) -> dict:
            processed_files.append(file)
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=2)
        files = [f"file{i}.csv" for i in range(10)]

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
        assert len(processed_files) == 10
        assert result.total == 10


class TestProgressTracking:
    """Test progress tracking with running/completed/failed counts."""

    def test_result_contains_counts(self):
        """BatchResult should contain total, completed, failed counts."""
        from rgrid.batch_executor import BatchExecutor, BatchResult

        # Arrange
        async def mock_submit(file: str) -> dict:
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = [f"file{i}.csv" for i in range(5)]

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
        assert isinstance(result, BatchResult)
        assert result.total == 5
        assert result.completed == 5
        assert result.failed == 0

    def test_progress_callback_called(self):
        """Progress callback should be called for each completion."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        progress_calls = []

        def progress_callback(completed: int, failed: int, total: int, running: int):
            progress_calls.append({
                "completed": completed,
                "failed": failed,
                "total": total,
                "running": running,
            })

        async def mock_submit(file: str) -> dict:
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=3)
        files = [f"file{i}.csv" for i in range(5)]

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

        asyncio.run(run_test())

        # Assert
        assert len(progress_calls) >= 5  # At least one call per file


class TestFailureHandling:
    """Test handling of partial failures."""

    def test_handles_partial_failures(self):
        """Batch should continue processing after individual failures."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        call_count = 0

        async def mock_submit(file: str) -> dict:
            nonlocal call_count
            call_count += 1
            if "file2" in file:
                raise Exception("Simulated failure")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = [f"file{i}.csv" for i in range(5)]

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
        assert call_count == 5, "All files should be attempted"
        assert result.completed == 4
        assert result.failed == 1
        assert len(result.execution_ids) == 4

    def test_multiple_failures_tracked(self):
        """Multiple failures should be tracked in result."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        async def mock_submit(file: str) -> dict:
            if "file" in file and int(file.replace("file", "").replace(".csv", "")) % 2 == 0:
                raise Exception("Even files fail")
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = [f"file{i}.csv" for i in range(6)]  # 0,1,2,3,4,5 - 0,2,4 fail

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
        assert result.failed == 3
        assert result.completed == 3
        assert len(result.failed_files) == 3
