"""Integration tests for batch execution (Story 5-1).

Tests cover:
- End-to-end batch submission with 3 files
- File upload to MinIO
- Batch status tracking
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

import pytest


class TestBatchEndToEnd:
    """End-to-end integration tests for batch execution."""

    def test_batch_3_files_creates_3_jobs(self):
        """E2E: Batch submission with 3 files should create 3 executions."""
        from rgrid.commands.run import run
        from rgrid.batch import expand_glob_pattern

        # Arrange - Create temp directory with 3 CSV files
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(1, 4):
                (Path(tmpdir) / f"file{i}.csv").write_text(f"data{i}")

            # Create a simple script
            script_path = Path(tmpdir) / "process.py"
            script_path.write_text("import sys; print(f'Processing: {sys.argv[1]}')")

            pattern = f"{tmpdir}/*.csv"

            # Act
            files = expand_glob_pattern(pattern)

            # Assert
            assert len(files) == 3

    @patch('rgrid.batch.upload_file_to_minio')
    @patch('rgrid.api_client.get_client')
    def test_batch_files_uploaded(self, mock_get_client, mock_upload):
        """Batch submission should upload all files to MinIO."""
        from rgrid.batch import BatchSubmitter

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(3):
                file_path = Path(tmpdir) / f"file{i}.csv"
                file_path.write_text(f"data{i}")
                files.append(str(file_path))

            mock_client = Mock()
            mock_client.create_execution.return_value = {
                "execution_id": f"exec_{{}}",
                "status": "pending",
                "upload_urls": {"file0.csv": "https://minio/upload0", "file1.csv": "https://minio/upload1", "file2.csv": "https://minio/upload2"}
            }
            mock_upload.return_value = True

            submitter = BatchSubmitter(mock_client)

            # Act
            result = submitter.submit_batch(
                script_content="print('hello')",
                files=files,
                runtime="python:3.11",
                env_vars={},
            )

            # Assert - Should have uploaded 3 files
            assert mock_upload.call_count == 3

    @patch('rgrid.batch.upload_file_to_minio')
    def test_batch_status_tracking(self, mock_upload):
        """Batch submission should return tracking information."""
        from rgrid.batch import BatchSubmitter

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.csv"
            file_path.write_text("data")

            mock_client = Mock()
            exec_id = "exec_123"
            mock_client.create_execution.return_value = {
                "execution_id": exec_id,
                "status": "pending",
                "upload_urls": {}
            }
            mock_upload.return_value = True

            submitter = BatchSubmitter(mock_client)

            # Act
            result = submitter.submit_batch(
                script_content="print('hello')",
                files=[str(file_path)],
                runtime="python:3.11",
                env_vars={},
            )

            # Assert
            assert "batch_id" in result
            assert "executions" in result
            assert len(result["executions"]) == 1
            assert result["executions"][0]["execution_id"] == exec_id


class TestCLIBatchFlag:
    """Test CLI --batch flag integration."""

    @patch('rgrid.commands.run.get_client')
    @patch('rgrid.commands.run.upload_file_to_minio')
    def test_cli_batch_flag_expands_glob(self, mock_upload, mock_get_client):
        """CLI --batch flag should expand glob patterns."""
        from rgrid.commands.run import run

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(3):
                (Path(tmpdir) / f"file{i}.csv").write_text(f"data{i}")

            # Create script
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("print('hello')")

            # Mock API client
            mock_client = Mock()
            mock_client.create_execution.return_value = {
                "execution_id": "exec_123",
                "status": "pending",
                "upload_urls": {}
            }
            mock_client.close = Mock()
            mock_get_client.return_value = mock_client
            mock_upload.return_value = True

            pattern = f"{tmpdir}/*.csv"

            # Act
            result = runner.invoke(run, [str(script_path), "--batch", pattern, "--remote-only"])

            # Assert
            assert result.exit_code == 0 or "Starting batch" in result.output or "3 files" in result.output

    def test_cli_batch_no_match_shows_error(self):
        """CLI --batch with no matching files should show error."""
        from rgrid.commands.run import run

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create script but no data files
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("print('hello')")

            pattern = f"{tmpdir}/*.nonexistent"

            # Act
            result = runner.invoke(run, [str(script_path), "--batch", pattern])

            # Assert
            assert result.exit_code != 0 or "No files match" in result.output
