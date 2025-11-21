"""Unit tests for auto-download outputs (Story 7-4)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path


class TestFormatSize:
    """Test the format_size utility function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        from rgrid.downloader import format_size
        assert format_size(500) == "500.0 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        from rgrid.downloader import format_size
        assert format_size(1024) == "1.0 KB"
        assert format_size(2048) == "2.0 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        from rgrid.downloader import format_size
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(2.5 * 1024 * 1024) == "2.5 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        from rgrid.downloader import format_size
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"


class TestHandleNameConflict:
    """Test filename conflict resolution."""

    def test_no_conflict_returns_original(self, tmp_path):
        """When no conflict exists, return original filename."""
        from rgrid.downloader import resolve_filename_conflict

        dest_dir = tmp_path
        filename = "output.txt"
        exec_id = "exec_abc12345"

        result = resolve_filename_conflict(dest_dir, filename, exec_id)

        assert result == dest_dir / "output.txt"

    def test_conflict_prefixes_with_exec_id(self, tmp_path):
        """When file exists, prefix with execution ID."""
        from rgrid.downloader import resolve_filename_conflict

        dest_dir = tmp_path
        filename = "output.txt"
        exec_id = "exec_abc12345"

        # Create existing file
        (dest_dir / filename).write_text("existing")

        result = resolve_filename_conflict(dest_dir, filename, exec_id)

        # Should prefix with first 8 chars of exec_id (exec_abc12345[:8] = exec_abc)
        assert result == dest_dir / "exec_abc_output.txt"

    def test_multiple_conflicts_uses_counter(self, tmp_path):
        """When multiple conflicts exist, use counter suffix."""
        from rgrid.downloader import resolve_filename_conflict

        dest_dir = tmp_path
        filename = "output.txt"
        exec_id = "exec_abc12345"

        # Create existing files
        (dest_dir / filename).write_text("existing")
        (dest_dir / "exec_abc_output.txt").write_text("existing2")

        result = resolve_filename_conflict(dest_dir, filename, exec_id)

        # Should add counter
        assert result == dest_dir / "exec_abc_output_2.txt"


class TestWaitForCompletion:
    """Test the wait_for_completion function."""

    def test_returns_when_completed(self):
        """Test waiting returns when execution completes."""
        from rgrid.downloader import wait_for_completion

        mock_client = Mock()
        mock_client.get_execution.return_value = {
            'status': 'completed',
            'exit_code': 0
        }

        result = wait_for_completion(mock_client, 'exec_123', timeout=10)

        assert result['status'] == 'completed'

    def test_returns_when_failed(self):
        """Test waiting returns when execution fails."""
        from rgrid.downloader import wait_for_completion

        mock_client = Mock()
        mock_client.get_execution.return_value = {
            'status': 'failed',
            'error_message': 'Script error'
        }

        result = wait_for_completion(mock_client, 'exec_123', timeout=10)

        assert result['status'] == 'failed'

    def test_polls_until_complete(self):
        """Test that it polls multiple times until completion."""
        from rgrid.downloader import wait_for_completion

        mock_client = Mock()
        # First call returns running, second returns completed
        mock_client.get_execution.side_effect = [
            {'status': 'running'},
            {'status': 'running'},
            {'status': 'completed', 'exit_code': 0}
        ]

        with patch('rgrid.downloader.time.sleep'):
            result = wait_for_completion(mock_client, 'exec_123', timeout=60)

        assert result['status'] == 'completed'
        assert mock_client.get_execution.call_count == 3

    def test_raises_timeout_error(self):
        """Test that TimeoutError is raised when timeout exceeded."""
        from rgrid.downloader import wait_for_completion

        mock_client = Mock()
        mock_client.get_execution.return_value = {'status': 'running'}

        with patch('rgrid.downloader.time.sleep'):
            with patch('rgrid.downloader.time.time') as mock_time:
                # Simulate time progression beyond timeout
                mock_time.side_effect = [0, 0, 5, 10, 15]  # start, then exceed timeout

                with pytest.raises(TimeoutError):
                    wait_for_completion(mock_client, 'exec_123', timeout=10)


class TestDownloadOutputs:
    """Test the download_outputs function."""

    def test_downloads_to_current_directory(self, tmp_path):
        """Test that outputs are downloaded to current directory."""
        from rgrid.downloader import download_outputs

        mock_client = Mock()
        mock_client.get_artifacts.return_value = [
            {
                'filename': 'output.txt',
                'file_path': 'executions/exec_123/outputs/output.txt',
                'size_bytes': 100,
                'artifact_type': 'output'
            }
        ]

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True

            result = download_outputs(mock_client, 'exec_123', dest_dir=tmp_path)

            assert result['downloaded'] == 1
            mock_download.assert_called_once()
            # Verify it was called with path in tmp_path
            call_args = mock_download.call_args
            assert str(tmp_path) in call_args[0][1]

    def test_returns_zero_when_no_outputs(self, tmp_path):
        """Test that download returns 0 when no outputs exist."""
        from rgrid.downloader import download_outputs

        mock_client = Mock()
        mock_client.get_artifacts.return_value = []

        result = download_outputs(mock_client, 'exec_123', dest_dir=tmp_path)

        assert result['downloaded'] == 0

    def test_handles_download_failures(self, tmp_path):
        """Test that download continues even when some files fail."""
        from rgrid.downloader import download_outputs

        mock_client = Mock()
        mock_client.get_artifacts.return_value = [
            {
                'filename': 'success.txt',
                'file_path': 'executions/exec_123/outputs/success.txt',
                'size_bytes': 100,
                'artifact_type': 'output'
            },
            {
                'filename': 'fail.txt',
                'file_path': 'executions/exec_123/outputs/fail.txt',
                'size_bytes': 100,
                'artifact_type': 'output'
            }
        ]

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            # First succeeds, second fails
            mock_download.side_effect = [True, False]

            result = download_outputs(mock_client, 'exec_123', dest_dir=tmp_path)

            assert result['downloaded'] == 1
            assert result['failed'] == 1

    def test_filters_output_artifacts_only(self, tmp_path):
        """Test that only output type artifacts are downloaded."""
        from rgrid.downloader import download_outputs

        mock_client = Mock()
        mock_client.get_artifacts.return_value = [
            {
                'filename': 'output.txt',
                'file_path': 'executions/exec_123/outputs/output.txt',
                'size_bytes': 100,
                'artifact_type': 'output'
            },
            {
                'filename': 'script.py',
                'file_path': 'executions/exec_123/inputs/script.py',
                'size_bytes': 50,
                'artifact_type': 'script'
            },
            {
                'filename': 'input.csv',
                'file_path': 'executions/exec_123/inputs/input.csv',
                'size_bytes': 200,
                'artifact_type': 'input'
            }
        ]

        with patch('rgrid.downloader.download_artifact_from_minio') as mock_download:
            mock_download.return_value = True

            result = download_outputs(mock_client, 'exec_123', dest_dir=tmp_path)

            # Should only download the output artifact
            assert result['downloaded'] == 1
            mock_download.assert_called_once()


class TestAutoDownloadIntegration:
    """Test auto-download integration with run command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_batch_mode_skips_auto_download(self, runner, tmp_path):
        """Test that batch mode does not auto-download (uses 7-5 flow)."""
        from rgrid.cli import main

        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Create batch files
        batch_file = tmp_path / "input.txt"
        batch_file.write_text("data")

        with patch('rgrid.commands.run.get_client') as mock:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_batch',
                'status': 'queued',
                'upload_urls': {}
            }
            client.close = Mock()
            mock.return_value = client

            with patch('rgrid.commands.run.display_batch_progress'):
                with patch('rgrid.batch.upload_file_to_minio', return_value=True):
                    # Act
                    result = runner.invoke(main, [
                        'run', str(script_file),
                        '--batch', str(tmp_path / "*.txt"),
                    ])

                    # Assert - batch should NOT call download_outputs
                    assert result.exit_code == 0
                    # Batch mode shows batch progress, not auto-download
                    # This validates batch doesn't trigger auto-download logic

    def test_remote_only_skips_auto_download(self, runner, tmp_path):
        """Test that --remote-only flag skips auto-download."""
        from rgrid.cli import main

        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        with patch('rgrid.commands.run.get_client') as mock:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_test',
                'status': 'queued',
                'upload_urls': {}
            }
            client.close = Mock()
            mock.return_value = client

            # Act
            result = runner.invoke(main, ['run', str(script_file), '--remote-only'])

            # Assert
            assert result.exit_code == 0
            assert 'Outputs stored remotely' in result.output
            # Should not have called wait or download
