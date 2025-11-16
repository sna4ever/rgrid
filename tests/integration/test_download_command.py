"""Integration tests for download command (Story 7-5)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from rgrid.cli import main


class TestDownloadCommand:
    """Test the rgrid download command for fetching outputs on demand."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for testing."""
        with patch('rgrid.commands.download.get_client') as mock:
            client = Mock()
            client.get_artifacts.return_value = [
                {
                    'artifact_id': 'art_1',
                    'filename': 'output1.txt',
                    'file_path': 'executions/exec_test/outputs/output1.txt',
                    'size_bytes': 100,
                    'artifact_type': 'output'
                },
                {
                    'artifact_id': 'art_2',
                    'filename': 'output2.txt',
                    'file_path': 'executions/exec_test/outputs/output2.txt',
                    'size_bytes': 200,
                    'artifact_type': 'output'
                }
            ]
            client.close = Mock()
            mock.return_value = client
            yield client

    def test_download_command_exists(self, runner):
        """Test that download command is registered and shows in help."""
        # Act
        result = runner.invoke(main, ['download', '--help'])

        # Assert
        assert result.exit_code == 0
        assert 'download' in result.output.lower()

    def test_download_command_fetches_outputs(self, runner, mock_api_client, tmp_path):
        """Test that download command fetches all output artifacts."""
        # Arrange
        exec_id = 'exec_test123'

        # Mock MinIO download
        with patch('rgrid.commands.download.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True

            # Act
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ['download', exec_id])

                # Assert
                assert result.exit_code == 0
                assert 'Downloaded 2 file(s)' in result.output
                assert mock_download.call_count == 2

    def test_download_to_custom_directory(self, runner, mock_api_client, tmp_path):
        """Test downloading artifacts to a custom output directory."""
        # Arrange
        exec_id = 'exec_test123'
        output_dir = tmp_path / "custom_output"

        # Mock MinIO download
        with patch('rgrid.commands.download.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True

            # Act
            result = runner.invoke(main, ['download', exec_id, '--output-dir', str(output_dir)])

            # Assert
            assert result.exit_code == 0
            assert mock_download.call_count == 2

    def test_download_no_artifacts(self, runner, tmp_path):
        """Test download command when execution has no output artifacts."""
        # Arrange
        exec_id = 'exec_no_outputs'

        with patch('rgrid.commands.download.get_client') as mock:
            client = Mock()
            client.get_artifacts.return_value = []
            client.close = Mock()
            mock.return_value = client

            # Act
            result = runner.invoke(main, ['download', exec_id])

            # Assert
            assert result.exit_code == 0
            assert 'No artifacts found' in result.output or 'Downloaded 0 file(s)' in result.output

    def test_list_available_outputs(self, runner, mock_api_client):
        """Test listing available outputs without downloading (--list flag)."""
        # Arrange
        exec_id = 'exec_test123'

        # Act
        result = runner.invoke(main, ['download', exec_id, '--list'])

        # Assert
        assert result.exit_code == 0
        assert 'output1.txt' in result.output
        assert 'output2.txt' in result.output
        assert '100' in result.output or '100 B' in result.output  # Size display

    def test_download_specific_file(self, runner, mock_api_client, tmp_path):
        """Test downloading only a specific file by name."""
        # Arrange
        exec_id = 'exec_test123'

        # Mock MinIO download
        with patch('rgrid.commands.download.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True

            # Act
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ['download', exec_id, '--file', 'output1.txt'])

                # Assert
                assert result.exit_code == 0
                # Should only download the specified file
                assert mock_download.call_count == 1

    def test_remote_only_with_batch(self, runner, tmp_path):
        """Test --remote-only flag works for 10-job batch."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Create 10 batch files
        batch_files = []
        for i in range(10):
            batch_file = tmp_path / f"input_{i}.txt"
            batch_file.write_text(f"data_{i}")
            batch_files.append(str(batch_file))

        with patch('rgrid.commands.run.get_client') as mock:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': f'exec_batch_{i}',
                'status': 'queued',
                'upload_urls': {}
            }
            client.get_batch_status.return_value = {
                'statuses': ['completed'] * 10
            }
            client.close = Mock()
            mock.return_value = client

            # Act
            with patch('rgrid.commands.run.display_batch_progress'):
                result = runner.invoke(main, [
                    'run', str(script_file),
                    *[arg for f in batch_files for arg in ['--batch', f]],
                    '--remote-only'
                ])

                # Assert
                assert result.exit_code == 0
                # Should create 10 executions
                assert client.create_execution.call_count == 10
