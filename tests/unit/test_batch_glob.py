"""Unit tests for batch glob expansion (Story 5-1).

Tests cover:
- Glob pattern expansion to matching files
- No-match error handling
- Batch execution creation
- Batch ID generation
- File argument passing to executions
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestGlobExpansion:
    """Test glob pattern expansion to matching files."""

    def test_glob_expands_matching_files(self):
        """When glob pattern matches files, should return list of file paths."""
        from rgrid.batch import expand_glob_pattern

        # Arrange - Create temp directory with CSV files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.csv").write_text("data1")
            (Path(tmpdir) / "file2.csv").write_text("data2")
            (Path(tmpdir) / "file3.csv").write_text("data3")
            (Path(tmpdir) / "other.txt").write_text("other")

            pattern = f"{tmpdir}/*.csv"

            # Act
            files = expand_glob_pattern(pattern)

            # Assert
            assert len(files) == 3
            filenames = [Path(f).name for f in files]
            assert "file1.csv" in filenames
            assert "file2.csv" in filenames
            assert "file3.csv" in filenames
            assert "other.txt" not in filenames

    def test_glob_no_match_raises_error(self):
        """When glob pattern matches no files, should raise ValueError."""
        from rgrid.batch import expand_glob_pattern

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            pattern = f"{tmpdir}/*.nonexistent"

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                expand_glob_pattern(pattern)

            assert "No files match pattern" in str(exc_info.value)

    def test_glob_returns_sorted_files(self):
        """Glob expansion should return files in sorted order."""
        from rgrid.batch import expand_glob_pattern

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "c.csv").write_text("c")
            (Path(tmpdir) / "a.csv").write_text("a")
            (Path(tmpdir) / "b.csv").write_text("b")

            pattern = f"{tmpdir}/*.csv"

            # Act
            files = expand_glob_pattern(pattern)

            # Assert
            filenames = [Path(f).name for f in files]
            assert filenames == ["a.csv", "b.csv", "c.csv"]


class TestBatchIdGeneration:
    """Test batch ID generation."""

    def test_batch_id_generated_with_prefix(self):
        """Batch ID should be generated with 'batch_' prefix."""
        from rgrid.batch import generate_batch_id

        # Act
        batch_id = generate_batch_id()

        # Assert
        assert batch_id.startswith("batch_")
        assert len(batch_id) > len("batch_")

    def test_batch_id_unique(self):
        """Each generated batch ID should be unique."""
        from rgrid.batch import generate_batch_id

        # Act
        ids = [generate_batch_id() for _ in range(100)]

        # Assert
        assert len(set(ids)) == 100  # All unique


class TestBatchExecution:
    """Test batch execution creation."""

    def test_batch_creates_n_executions(self):
        """Batch submission should create one execution per file."""
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
                "execution_id": "exec_123",
                "status": "pending",
                "upload_urls": {}
            }

            submitter = BatchSubmitter(mock_client)
            script_content = "print('hello')"

            # Act
            result = submitter.submit_batch(
                script_content=script_content,
                files=files,
                runtime="python:3.11",
                env_vars={},
            )

            # Assert
            assert mock_client.create_execution.call_count == 3
            assert len(result["executions"]) == 3

    def test_each_execution_gets_file_arg(self):
        """Each execution should receive its input file as argument."""
        from rgrid.batch import BatchSubmitter

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.csv"
            file_path.write_text("data")

            mock_client = Mock()
            mock_client.create_execution.return_value = {
                "execution_id": "exec_123",
                "status": "pending",
                "upload_urls": {}
            }

            submitter = BatchSubmitter(mock_client)
            script_content = "print('hello')"

            # Act
            submitter.submit_batch(
                script_content=script_content,
                files=[str(file_path)],
                runtime="python:3.11",
                env_vars={},
            )

            # Assert
            call_kwargs = mock_client.create_execution.call_args[1]
            # The filename should be in input_files
            assert "test.csv" in call_kwargs["input_files"]

    def test_batch_returns_batch_id(self):
        """Batch submission should return a batch ID."""
        from rgrid.batch import BatchSubmitter

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.csv"
            file_path.write_text("data")

            mock_client = Mock()
            mock_client.create_execution.return_value = {
                "execution_id": "exec_123",
                "status": "pending",
                "upload_urls": {}
            }

            submitter = BatchSubmitter(mock_client)
            script_content = "print('hello')"

            # Act
            result = submitter.submit_batch(
                script_content=script_content,
                files=[str(file_path)],
                runtime="python:3.11",
                env_vars={},
            )

            # Assert
            assert "batch_id" in result
            assert result["batch_id"].startswith("batch_")

    def test_batch_uploads_files(self):
        """Batch submission should upload each file."""
        from rgrid.batch import BatchSubmitter

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.csv"
            file_path.write_text("data")

            mock_client = Mock()
            mock_client.create_execution.return_value = {
                "execution_id": "exec_123",
                "status": "pending",
                "upload_urls": {"test.csv": "https://minio/upload"}
            }

            submitter = BatchSubmitter(mock_client)
            script_content = "print('hello')"

            # Act
            with patch('rgrid.batch.upload_file_to_minio') as mock_upload:
                mock_upload.return_value = True
                submitter.submit_batch(
                    script_content=script_content,
                    files=[str(file_path)],
                    runtime="python:3.11",
                    env_vars={},
                )

                # Assert
                mock_upload.assert_called_once()
