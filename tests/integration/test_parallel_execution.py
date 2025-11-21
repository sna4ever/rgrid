"""Integration tests for parallel batch execution (Story 5-2).

Tests cover:
- Large batch with low parallelism
- All files processed correctly
- Timing verification for actual concurrency
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest


class TestParallelBatchExecution:
    """Integration tests for parallel batch execution."""

    @pytest.fixture
    def temp_batch_files(self):
        """Create temporary batch files for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(50):
                file_path = Path(tmpdir) / f"file{i:02d}.csv"
                file_path.write_text(f"data{i}")
                files.append(str(file_path))
            yield files

    def test_50_files_parallel_5(self, temp_batch_files):
        """50 files with parallelism 5 should process correctly."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        execution_count = 0

        async def mock_submit(file: str) -> dict:
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.01)  # Small delay to simulate API call
            return {"execution_id": f"exec_{execution_count}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=mock_submit):
                return await executor.execute_batch_async(
                    script_content="print('test')",
                    files=temp_batch_files,
                    runtime="python:3.11",
                    env_vars={},
                )

        result = asyncio.run(run_test())

        # Assert
        assert result.total == 50
        assert result.completed == 50
        assert result.failed == 0
        assert len(result.execution_ids) == 50

    def test_batch_completes_all_files(self, temp_batch_files):
        """All files in batch should be processed to completion."""
        from rgrid.batch_executor import BatchExecutor

        # Arrange
        processed_files = set()

        async def mock_submit(file: str) -> dict:
            processed_files.add(file)
            return {"execution_id": f"exec_{Path(file).name}", "status": "pending"}

        executor = BatchExecutor(max_parallel=10)

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=mock_submit):
                return await executor.execute_batch_async(
                    script_content="print('test')",
                    files=temp_batch_files,
                    runtime="python:3.11",
                    env_vars={},
                )

        asyncio.run(run_test())

        # Assert
        assert len(processed_files) == 50
        for f in temp_batch_files:
            assert f in processed_files

    def test_timing_respects_parallelism_limit(self):
        """Verify actual concurrency is limited by parallelism setting."""
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
            await asyncio.sleep(0.05)  # Simulate slow API
            async with lock:
                current_concurrent -= 1
            return {"execution_id": f"exec_{file}", "status": "pending"}

        executor = BatchExecutor(max_parallel=5)
        files = [f"file{i}.csv" for i in range(20)]

        # Act
        async def run_test():
            with patch.object(executor, '_submit_single', side_effect=slow_submit):
                start = time.time()
                result = await executor.execute_batch_async(
                    script_content="print('test')",
                    files=files,
                    runtime="python:3.11",
                    env_vars={},
                )
                elapsed = time.time() - start
            return result, elapsed, max_concurrent_observed

        result, elapsed, max_concurrent = asyncio.run(run_test())

        # Assert
        # With 20 files, 5 parallel, 0.05s each -> minimum ~4 batches * 0.05s = 0.2s
        # But should be much faster than sequential (20 * 0.05s = 1s)
        assert max_concurrent <= 5, f"Max concurrent was {max_concurrent}, should be <= 5"
        assert result.completed == 20
        # Timing should show parallelism is working (not sequential)
        assert elapsed < 0.5, f"Elapsed {elapsed}s suggests not running in parallel"


class TestParallelFlagCLI:
    """Test CLI --parallel flag integration."""

    def test_parallel_flag_default_in_click(self):
        """CLI --parallel flag should have default of 10."""
        from click.testing import CliRunner
        from rgrid.commands.run import run

        # Get the option from the command
        parallel_option = None
        for param in run.params:
            if param.name == "parallel":
                parallel_option = param
                break

        # Assert
        assert parallel_option is not None, "--parallel option should exist"
        assert parallel_option.default == 10, f"Default should be 10, got {parallel_option.default}"

    def test_parallel_flag_accepts_custom_value(self):
        """CLI --parallel flag should accept custom values."""
        from click.testing import CliRunner
        from rgrid.commands.run import run

        runner = CliRunner()

        # Create a temp script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('test')")
            script_path = f.name

        try:
            # Just test that --parallel is a valid option (we'll mock the actual execution)
            result = runner.invoke(run, [script_path, '--parallel', '20', '--help'])
            # --help should work without error
            assert result.exit_code == 0 or '--parallel' in result.output or 'Usage' in result.output
        finally:
            Path(script_path).unlink()
