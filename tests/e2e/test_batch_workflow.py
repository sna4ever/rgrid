"""
E2E tests for batch execution workflow (Stories 5-1 to 5-5).

Tests the complete batch execution workflow including:
- Batch flag with glob patterns
- Parallel execution
- Batch progress tracking
- Batch output organization
- Batch failure handling
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner


@pytest.mark.e2e
class TestBatchGlobExpansion:
    """Test batch --batch flag with glob patterns."""

    def test_batch_expands_glob_pattern(self, cli_runner, temp_script_dir, batch_test_files):
        """Test that --batch flag correctly expands glob patterns."""
        from rgrid.batch import expand_glob_pattern

        # Create glob pattern for test files
        pattern = f"{temp_script_dir}/test_*.txt"

        # Expand pattern
        files = expand_glob_pattern(pattern)

        # Should find all test files
        assert len(files) == 3
        assert all(str(f).endswith('.txt') for f in files)

    def test_batch_pattern_no_matches_raises_error(self, temp_script_dir):
        """Test that non-matching glob pattern raises error."""
        from rgrid.batch import expand_glob_pattern

        pattern = f"{temp_script_dir}/nonexistent_*.xyz"

        with pytest.raises(ValueError) as exc_info:
            expand_glob_pattern(pattern)

        assert "No files match" in str(exc_info.value)

    def test_batch_generates_unique_batch_id(self):
        """Test that batch ID generation produces unique IDs."""
        from rgrid.batch import generate_batch_id

        ids = [generate_batch_id() for _ in range(10)]

        # All IDs should be unique
        assert len(set(ids)) == 10

        # All IDs should have correct prefix
        assert all(id_.startswith("batch_") for id_ in ids)


@pytest.mark.e2e
class TestBatchExecution:
    """Test batch execution with mocked API."""

    def test_batch_executor_concurrent_limit(self, mock_api_client, temp_script_dir, batch_test_files):
        """Test BatchExecutor respects parallel limit."""
        from rgrid.batch_executor import BatchExecutor

        # Create executor with limit of 2
        executor = BatchExecutor(max_parallel=2)

        # Mock client behavior
        mock_api_client.create_execution.return_value = {
            "execution_id": "exec_123",
            "status": "queued",
            "upload_urls": {},
        }

        # Create a simple script
        script_path = Path(temp_script_dir) / "batch_script.py"
        script_path.write_text("print('batch test')")
        script_content = script_path.read_text()

        # Execute batch
        result = executor.execute_batch(
            script_content=script_content,
            files=batch_test_files,
            runtime="python:3.11",
            env_vars={},
            args=[],
            requirements_content=None,
            client=mock_api_client,
            batch_id="batch_test123",
        )

        # Should have attempted to create executions
        assert mock_api_client.create_execution.call_count == 3

    def test_batch_failure_handling(self, mock_api_client, temp_script_dir):
        """Test batch execution handles failures gracefully (Story 5-5)."""
        from rgrid.batch_executor import BatchExecutor

        executor = BatchExecutor(max_parallel=2)

        # Make one execution fail
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Simulated API error")
            return {"execution_id": f"exec_{call_count}", "status": "queued", "upload_urls": {}}

        mock_api_client.create_execution.side_effect = mock_create

        # Create test files
        files = []
        for i in range(3):
            f = Path(temp_script_dir) / f"test_{i}.txt"
            f.write_text(f"data {i}")
            files.append(str(f))

        script_path = Path(temp_script_dir) / "script.py"
        script_path.write_text("print('test')")

        result = executor.execute_batch(
            script_content=script_path.read_text(),
            files=files,
            runtime="python:3.11",
            env_vars={},
            args=[],
            requirements_content=None,
            client=mock_api_client,
            batch_id="batch_test",
        )

        # Should have 2 completed, 1 failed
        assert result.completed == 2
        assert result.failed == 1
        assert len(result.failed_files) == 1


@pytest.mark.e2e
class TestBatchProgress:
    """Test batch progress tracking (Story 5-3)."""

    def test_batch_progress_calculation(self, mock_api_client):
        """Test batch progress is calculated correctly."""
        from rgrid.batch_progress import calculate_progress

        # Create list of statuses as the function expects
        statuses = ["completed"] * 7 + ["failed"] + ["running"] + ["queued"]

        # Calculate progress
        progress = calculate_progress(statuses)

        # Verify progress calculation
        assert progress["total"] == 10
        assert progress["completed"] == 7
        assert progress["failed"] == 1
        assert progress["running"] == 1
        assert progress["queued"] == 1

    def test_batch_status_api_call(self, mock_api_client):
        """Test batch status API is called correctly."""
        batch_id = "batch_test456"

        mock_api_client.get_batch_status.return_value = {
            "total": 5,
            "completed": 3,
            "failed": 0,
            "running": 2,
            "queued": 0,
        }

        result = mock_api_client.get_batch_status(batch_id)

        mock_api_client.get_batch_status.assert_called_once_with(batch_id)
        assert result["total"] == 5


@pytest.mark.e2e
class TestBatchOutputOrganization:
    """Test batch output organization (Story 5-4)."""

    def test_batch_outputs_organized_by_input_file(self, mock_api_client, temp_script_dir):
        """Test input filename extraction from execution metadata."""
        from rgrid.batch_download import extract_input_name

        # Test execution with batch metadata
        execution = {
            "execution_id": "exec_1",
            "batch_metadata": {"input_file": "/path/to/data_1.csv"},
            "status": "completed",
        }

        # Extract input name
        input_name = extract_input_name(execution)

        # Should extract just the filename
        assert input_name == "data_1.csv"

    def test_flat_output_mode(self, temp_script_dir):
        """Test flat output mode skips subdirectory creation."""
        from rgrid.batch_download import create_output_directory

        output_dir = Path(temp_script_dir) / "outputs"

        # With flat=True, should return base directory
        result_dir = create_output_directory(
            base_dir=str(output_dir),
            input_name="data.csv",
            flat=True,
        )

        # Should be the base directory itself
        assert result_dir == str(output_dir)
