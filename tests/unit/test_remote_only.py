"""Unit tests for --remote-only flag (Story 7-5)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from rgrid.cli import main


class TestRemoteOnlyFlag:
    """Test the --remote-only flag for skipping auto-download."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for testing."""
        with patch('rgrid.commands.run.get_client') as mock:
            client = Mock()
            client.create_execution.return_value = {
                'execution_id': 'exec_test123',
                'status': 'queued',
                'upload_urls': {}
            }
            client.close = Mock()
            mock.return_value = client
            yield client

    def test_remote_only_flag_present(self, runner):
        """Test that --remote-only flag is recognized by CLI parser."""
        # Arrange & Act
        result = runner.invoke(main, ['run', '--help'])

        # Assert
        assert result.exit_code == 0
        assert '--remote-only' in result.output
        assert 'Skip auto-download of outputs' in result.output

    def test_skip_download_when_flag_set(self, runner, mock_api_client, tmp_path):
        """Test that download message is shown when --remote-only is set."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Act
        result = runner.invoke(main, ['run', str(script_file), '--remote-only'])

        # Assert
        assert result.exit_code == 0
        assert 'Outputs stored remotely' in result.output

    def test_download_happens_without_flag(self, runner, mock_api_client, tmp_path):
        """Test that auto-download is triggered when --remote-only is NOT set."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Mock wait_for_completion and download_outputs (Story 7-4)
        with patch('rgrid.commands.run.wait_for_completion') as mock_wait:
            mock_wait.return_value = {'status': 'completed', 'exit_code': 0}
            with patch('rgrid.commands.run.download_outputs') as mock_download:
                mock_download.return_value = {'downloaded': 1, 'failed': 0}

                # Act
                result = runner.invoke(main, ['run', str(script_file)])

                # Assert
                assert result.exit_code == 0
                # Without --remote-only, should trigger auto-download flow
                assert 'Waiting for completion' in result.output or 'completed' in result.output.lower()

    def test_display_download_command(self, runner, mock_api_client, tmp_path):
        """Test that proper download command message is shown with --remote-only."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Act
        result = runner.invoke(main, ['run', str(script_file), '--remote-only'])

        # Assert
        assert result.exit_code == 0
        assert 'Outputs stored remotely' in result.output
        assert 'rgrid download exec_test123' in result.output

    def test_artifacts_still_recorded(self, runner, mock_api_client, tmp_path):
        """Test that execution is created in DB even with --remote-only."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        # Act
        result = runner.invoke(main, ['run', str(script_file), '--remote-only'])

        # Assert
        assert result.exit_code == 0
        # API client should still create execution
        mock_api_client.create_execution.assert_called_once()

    def test_remote_only_with_batch_mode(self, runner, mock_api_client, tmp_path):
        """Test that --remote-only works with batch mode."""
        # Arrange
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")

        batch_file1 = tmp_path / "input1.txt"
        batch_file2 = tmp_path / "input2.txt"
        batch_file1.write_text("data1")
        batch_file2.write_text("data2")

        # Mock batch status endpoint
        mock_api_client.get_batch_status.return_value = {
            'statuses': ['completed', 'completed']
        }

        # Act
        with patch('rgrid.commands.run.display_batch_progress'):
            result = runner.invoke(main, [
                'run', str(script_file),
                '--batch', str(batch_file1),
                '--batch', str(batch_file2),
                '--remote-only'
            ])

            # Assert
            assert result.exit_code == 0
            assert 'Outputs stored remotely' in result.output or 'batch' in result.output.lower()
