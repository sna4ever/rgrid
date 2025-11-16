"""Unit tests for output file collection (Story 7-2)."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Will implement these modules
# from runner.output_collector import collect_output_files, upload_outputs_to_minio


class TestOutputCollector:
    """Test output file collection from /work directory."""

    def test_collect_empty_work_directory(self, tmp_path):
        """AC #1: Empty /work directory returns empty list."""
        from runner.output_collector import collect_output_files

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        outputs = collect_output_files(work_dir)

        assert outputs == []

    def test_collect_single_output_file(self, tmp_path):
        """AC #3: Scan /work and find all files."""
        from runner.output_collector import collect_output_files

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create output file
        output_file = work_dir / "result.txt"
        output_file.write_text("test output")

        outputs = collect_output_files(work_dir)

        assert len(outputs) == 1
        assert outputs[0]["filename"] == "result.txt"
        assert outputs[0]["size_bytes"] == 11  # "test output" = 11 bytes
        assert outputs[0]["path"] == str(output_file)

    def test_collect_multiple_output_files(self, tmp_path):
        """AC #3: Collect all files in /work."""
        from runner.output_collector import collect_output_files

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create multiple files
        (work_dir / "output1.csv").write_text("data1")
        (work_dir / "output2.json").write_text('{"key": "value"}')
        (work_dir / "result.png").write_bytes(b"\x89PNG\r\n")  # Binary file

        outputs = collect_output_files(work_dir)

        assert len(outputs) == 3
        filenames = [f["filename"] for f in outputs]
        assert "output1.csv" in filenames
        assert "output2.json" in filenames
        assert "result.png" in filenames

    def test_collect_files_in_subdirectories(self, tmp_path):
        """AC #3 + Tech Spec: Subdirectories in /work preserved in S3 path."""
        from runner.output_collector import collect_output_files

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create subdirectory with file
        subdir = work_dir / "results"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested output")

        outputs = collect_output_files(work_dir)

        assert len(outputs) == 1
        assert outputs[0]["filename"] == "results/nested.txt"  # Preserve subdir path

    @patch('runner.output_collector.boto3.client')
    def test_upload_outputs_to_minio(self, mock_boto_client, tmp_path):
        """AC #4: Upload all outputs to MinIO with correct keys."""
        from runner.output_collector import upload_outputs_to_minio

        # Setup mock MinIO client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        output_file = work_dir / "result.txt"
        output_file.write_text("test")

        exec_id = "exec_abc123"
        outputs = [{"filename": "result.txt", "path": str(output_file), "size_bytes": 4}]

        uploaded = upload_outputs_to_minio(outputs, exec_id)

        # Verify upload was called with correct S3 key
        mock_s3.upload_file.assert_called_once()
        call_args = mock_s3.upload_file.call_args
        assert call_args[1]["Key"] == "executions/exec_abc123/outputs/result.txt"
        assert len(uploaded) == 1
        assert uploaded[0]["s3_key"] == "executions/exec_abc123/outputs/result.txt"

    def test_get_content_type(self):
        """Helper test: Detect content type from filename."""
        from runner.output_collector import get_content_type

        assert get_content_type("file.txt") == "text/plain"
        assert get_content_type("data.csv") == "text/csv"
        assert get_content_type("config.json") == "application/json"
        assert get_content_type("image.png") == "image/png"
        assert get_content_type("unknown.unknownext") == "application/octet-stream"
