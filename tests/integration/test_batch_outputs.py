"""Integration tests for batch output organization (Tier 5 - Story 5-4)."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


class TestBatchOutputOrganization:
    """Test organizing batch outputs into directories."""

    def test_batch_outputs_organized(self):
        """10 files → 10 output dirs."""
        from cli.rgrid.batch_download import organize_batch_outputs

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_api = Mock()

            # Simulate 10 executions with different input files
            executions = [
                {"execution_id": f"exec_{i}", "batch_metadata": {"input_file": f"file{i}.csv"}}
                for i in range(10)
            ]

            # Mock artifacts for each execution
            def get_artifacts(exec_id):
                return [
                    {"file_key": f"{exec_id}/output.txt", "filename": "output.txt"}
                ]

            mock_api.get_artifacts = Mock(side_effect=get_artifacts)
            mock_api.download_artifact = Mock()

            # Act
            organize_batch_outputs(
                mock_api,
                executions,
                output_dir=tmpdir,
                flat=False
            )

            # Assert
            # Should create 10 subdirectories
            created_dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            assert len(created_dirs) == 10

            # Check specific directories exist
            for i in range(10):
                expected_dir = os.path.join(tmpdir, f"file{i}.csv")
                assert os.path.exists(expected_dir)
                assert os.path.isdir(expected_dir)

    def test_nested_output_structure(self):
        """Subdirectories preserved in outputs."""
        from cli.rgrid.batch_download import organize_batch_outputs

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_api = Mock()

            executions = [
                {"execution_id": "exec_1", "batch_metadata": {"input_file": "data.csv"}}
            ]

            # Mock artifacts with nested paths
            def get_artifacts(exec_id):
                return [
                    {"file_key": f"{exec_id}/results/output.txt", "filename": "results/output.txt"},
                    {"file_key": f"{exec_id}/logs/debug.log", "filename": "logs/debug.log"}
                ]

            mock_api.get_artifacts = Mock(side_effect=get_artifacts)

            downloaded_files = []

            def download_artifact(artifact, target_path):
                downloaded_files.append(target_path)
                # Create the file
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                Path(target_path).touch()

            mock_api.download_artifact = Mock(side_effect=download_artifact)

            # Act
            organize_batch_outputs(
                mock_api,
                executions,
                output_dir=tmpdir,
                flat=False
            )

            # Assert
            # Should preserve subdirectory structure
            assert os.path.exists(os.path.join(tmpdir, "data.csv", "results", "output.txt"))
            assert os.path.exists(os.path.join(tmpdir, "data.csv", "logs", "debug.log"))

    def test_custom_output_location(self):
        """Files go to custom directory with --output-dir flag."""
        from cli.rgrid.batch_download import organize_batch_outputs

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = os.path.join(tmpdir, "my", "custom", "location")
            mock_api = Mock()

            executions = [
                {"execution_id": "exec_1", "batch_metadata": {"input_file": "file1.csv"}},
                {"execution_id": "exec_2", "batch_metadata": {"input_file": "file2.csv"}}
            ]

            mock_api.get_artifacts = Mock(return_value=[])
            mock_api.download_artifact = Mock()

            # Act
            organize_batch_outputs(
                mock_api,
                executions,
                output_dir=custom_dir,
                flat=False
            )

            # Assert
            # Should create directories under custom location
            assert os.path.exists(os.path.join(custom_dir, "file1.csv"))
            assert os.path.exists(os.path.join(custom_dir, "file2.csv"))

    def test_flat_output_mode(self):
        """All files in one directory with --flat flag."""
        from cli.rgrid.batch_download import organize_batch_outputs

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_api = Mock()

            executions = [
                {"execution_id": "exec_1", "batch_metadata": {"input_file": "file1.csv"}},
                {"execution_id": "exec_2", "batch_metadata": {"input_file": "file2.csv"}},
                {"execution_id": "exec_3", "batch_metadata": {"input_file": "file3.csv"}}
            ]

            downloaded_files = []

            def get_artifacts(exec_id):
                return [
                    {"file_key": f"{exec_id}/output.txt", "filename": "output.txt"}
                ]

            def download_artifact(artifact, target_path):
                downloaded_files.append(target_path)
                Path(target_path).touch()

            mock_api.get_artifacts = Mock(side_effect=get_artifacts)
            mock_api.download_artifact = Mock(side_effect=download_artifact)

            # Act
            organize_batch_outputs(
                mock_api,
                executions,
                output_dir=tmpdir,
                flat=True  # Flat mode
            )

            # Assert
            # Should NOT create subdirectories
            dirs_created = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            # In flat mode, no subdirectories for inputs should be created
            assert "file1.csv" not in dirs_created
            assert "file2.csv" not in dirs_created
            assert "file3.csv" not in dirs_created

            # All files should be directly in tmpdir
            for file_path in downloaded_files:
                assert os.path.dirname(file_path) == tmpdir or tmpdir in file_path


class TestBatchDownloadIntegration:
    """Test full batch download workflow."""

    def test_batch_download_with_progress(self):
        """Download batch outputs with progress indicator."""
        from cli.rgrid.batch_download import download_batch_outputs

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_api = Mock()
            batch_id = "test-batch-123"

            # Mock batch executions
            executions = [
                {"execution_id": f"exec_{i}", "batch_metadata": {"input_file": f"input{i}.txt"}}
                for i in range(5)
            ]

            mock_api.get_batch_executions = Mock(return_value=executions)
            mock_api.get_artifacts = Mock(return_value=[
                {"file_key": "exec_1/output.txt", "filename": "output.txt"}
            ])
            mock_api.download_artifact = Mock()

            # Act
            with patch('builtins.print'):  # Suppress progress output
                download_batch_outputs(
                    mock_api,
                    batch_id,
                    output_dir=tmpdir,
                    flat=False
                )

            # Assert
            assert mock_api.get_batch_executions.called
            assert mock_api.get_batch_executions.call_args[0][0] == batch_id
