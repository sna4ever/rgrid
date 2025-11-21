"""Integration tests for auto-download outputs (Story 7-4)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from rgrid.cli import main


class TestAutoDownloadAfterExecution:
    """Test automatic download of outputs after execution completes."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_completed_execution(self):
        """Mock a completed execution with outputs."""
        with patch('rgrid.commands.run.get_client') as mock_get:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_test123',
                'status': 'queued',
                'upload_urls': {}
            }
            client.get_execution.return_value = {
                'execution_id': 'exec_test123',
                'status': 'completed',
                'exit_code': 0
            }
            client.get_artifacts.return_value = [
                {
                    'filename': 'output.json',
                    'file_path': 'executions/exec_test123/outputs/output.json',
                    'size_bytes': 1200,
                    'artifact_type': 'output'
                },
                {
                    'filename': 'results.csv',
                    'file_path': 'executions/exec_test123/outputs/results.csv',
                    'size_bytes': 500,
                    'artifact_type': 'output'
                }
            ]
            client.close = Mock()
            mock_get.return_value = client
            yield client

    def test_outputs_downloaded_after_completion(self, runner, mock_completed_execution, tmp_path):
        """Test that outputs are automatically downloaded when execution completes."""
        # Arrange
        script_file = tmp_path / "process.py"
        script_file.write_text("print('processing')")

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True
            with patch('rgrid.downloader.time.sleep'):  # Speed up polling

                # Act
                with runner.isolated_filesystem(temp_dir=tmp_path):
                    result = runner.invoke(main, ['run', str(script_file)])

                    # Assert
                    assert result.exit_code == 0
                    # Should show download progress
                    assert 'Downloaded' in result.output or 'output.json' in result.output

    def test_multiple_files_downloaded(self, runner, mock_completed_execution, tmp_path):
        """Test that all output files are downloaded."""
        # Arrange
        script_file = tmp_path / "process.py"
        script_file.write_text("print('processing')")

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True
            with patch('rgrid.downloader.time.sleep'):

                # Act
                with runner.isolated_filesystem(temp_dir=tmp_path):
                    result = runner.invoke(main, ['run', str(script_file)])

                    # Assert
                    assert result.exit_code == 0
                    # Should download both files
                    assert mock_download.call_count == 2

    def test_shows_file_sizes(self, runner, mock_completed_execution, tmp_path):
        """Test that file sizes are displayed during download."""
        # Arrange
        script_file = tmp_path / "process.py"
        script_file.write_text("print('processing')")

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True
            with patch('rgrid.downloader.time.sleep'):

                # Act
                with runner.isolated_filesystem(temp_dir=tmp_path):
                    result = runner.invoke(main, ['run', str(script_file)])

                    # Assert
                    assert result.exit_code == 0
                    # Should show sizes (KB or B)
                    assert 'KB' in result.output or 'B' in result.output or 'MB' in result.output


class TestDownloadErrorHandling:
    """Test error handling during auto-download."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_failed_execution_no_download(self, runner, tmp_path):
        """Test that failed executions don't trigger download."""
        # Arrange
        script_file = tmp_path / "failing.py"
        script_file.write_text("raise Exception('fail')")

        with patch('rgrid.commands.run.get_client') as mock_get:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_fail',
                'status': 'queued',
                'upload_urls': {}
            }
            client.get_execution.return_value = {
                'execution_id': 'exec_fail',
                'status': 'failed',
                'error_message': 'Script raised exception'
            }
            client.close = Mock()
            mock_get.return_value = client

            with patch('rgrid.downloader.time.sleep'):
                with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:

                    # Act
                    result = runner.invoke(main, ['run', str(script_file)])

                    # Assert
                    # Download should not be called for failed execution
                    mock_download.assert_not_called()
                    assert 'failed' in result.output.lower() or 'error' in result.output.lower()

    def test_no_outputs_graceful_handling(self, runner, tmp_path):
        """Test graceful handling when execution has no outputs."""
        # Arrange
        script_file = tmp_path / "no_output.py"
        script_file.write_text("print('no files created')")

        with patch('rgrid.commands.run.get_client') as mock_get:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_empty',
                'status': 'queued',
                'upload_urls': {}
            }
            client.get_execution.return_value = {
                'execution_id': 'exec_empty',
                'status': 'completed',
                'exit_code': 0
            }
            client.get_artifacts.return_value = []  # No outputs
            client.close = Mock()
            mock_get.return_value = client

            with patch('rgrid.downloader.time.sleep'):

                # Act
                result = runner.invoke(main, ['run', str(script_file)])

                # Assert
                assert result.exit_code == 0
                assert 'No output' in result.output or '0 files' in result.output or 'completed' in result.output.lower()


class TestDownloadProgress:
    """Test download progress display."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_large_file_shows_progress(self, runner, tmp_path):
        """Test that large files show download progress."""
        # Arrange
        script_file = tmp_path / "large_output.py"
        script_file.write_text("# generates large file")

        with patch('rgrid.commands.run.get_client') as mock_get:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_large',
                'status': 'queued',
                'upload_urls': {}
            }
            client.get_execution.return_value = {
                'execution_id': 'exec_large',
                'status': 'completed',
                'exit_code': 0
            }
            client.get_artifacts.return_value = [
                {
                    'filename': 'large_data.bin',
                    'file_path': 'executions/exec_large/outputs/large_data.bin',
                    'size_bytes': 100 * 1024 * 1024,  # 100 MB
                    'artifact_type': 'output'
                }
            ]
            client.close = Mock()
            mock_get.return_value = client

            with patch('rgrid.downloader.time.sleep'):
                with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
                    mock_download.return_value = True

                    # Act
                    result = runner.invoke(main, ['run', str(script_file)])

                    # Assert
                    assert result.exit_code == 0
                    # Should show size indicator
                    assert 'MB' in result.output or 'large_data' in result.output
