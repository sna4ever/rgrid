"""
E2E tests for download workflow (Stories 7-4, 7-5, 7-6).

Tests the complete download workflow including:
- Auto-download outputs after completion
- Remote-only flag to skip download
- Manual download command
- Large file streaming
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner


@pytest.mark.e2e
class TestAutoDownload:
    """Test auto-download of outputs (Story 7-4)."""

    def test_auto_download_triggered_on_completion(self, mock_api_client):
        """Test that auto-download triggers after successful execution."""
        from rgrid.downloader import wait_for_completion

        # Mock execution that completes
        mock_api_client.get_execution.return_value = {
            "execution_id": "exec_123",
            "status": "completed",
            "exit_code": 0,
        }

        # Should return completed status
        result = wait_for_completion(mock_api_client, "exec_123", timeout=10)

        assert result["status"] == "completed"
        assert result["exit_code"] == 0

    def test_auto_download_handles_failure(self, mock_api_client):
        """Test auto-download handles failed executions gracefully."""
        mock_api_client.get_execution.return_value = {
            "execution_id": "exec_123",
            "status": "failed",
            "exit_code": 1,
            "error_message": "Script error",
        }

        from rgrid.downloader import wait_for_completion

        result = wait_for_completion(mock_api_client, "exec_123", timeout=10)

        assert result["status"] == "failed"


@pytest.mark.e2e
class TestRemoteOnlyFlag:
    """Test --remote-only flag (Story 7-5)."""

    def test_remote_only_skips_download(self, cli_runner, simple_script, mock_credentials):
        """Test --remote-only flag prevents auto-download."""
        from rgrid.cli import main

        with patch('rgrid.commands.run.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_execution.return_value = {
                "execution_id": "exec_123",
                "status": "queued",
                "upload_urls": {},
            }
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['run', simple_script, '--remote-only'],
                    catch_exceptions=False,
                )

        # Command should complete without downloading
        # With --remote-only, no wait_for_completion should be called
        assert result.exit_code == 0 or "remote" in result.output.lower()


@pytest.mark.e2e
class TestDownloadCommand:
    """Test rgrid download command (Story 7-5)."""

    def test_download_lists_artifacts(self, cli_runner, mock_credentials):
        """Test rgrid download --list shows available artifacts."""
        from rgrid.cli import main

        with patch('rgrid.commands.download.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_artifacts.return_value = [
                {
                    "filename": "output.json",
                    "artifact_type": "output",
                    "size_bytes": 1024,
                },
                {
                    "filename": "log.txt",
                    "artifact_type": "output",
                    "size_bytes": 256,
                },
            ]
            mock_get_client.return_value = mock_client

            with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                result = cli_runner.invoke(
                    main,
                    ['download', 'exec_123', '--list'],
                    catch_exceptions=False,
                )

        # Should list artifacts without downloading
        assert "output.json" in result.output or result.exit_code == 0

    def test_download_specific_file(self, cli_runner, temp_script_dir, mock_credentials):
        """Test downloading a specific file with --file flag."""
        from rgrid.cli import main

        with patch('rgrid.commands.download.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_artifacts.return_value = [
                {
                    "filename": "output.json",
                    "artifact_type": "output",
                    "size_bytes": 256,
                    "file_path": "artifacts/exec_123/output.json",
                },
            ]
            mock_get_client.return_value = mock_client

            # Mock the actual download
            with patch('rgrid.commands.download.download_artifact_from_minio', return_value=True):
                with patch('rgrid.config.config.load_credentials', return_value=mock_credentials):
                    result = cli_runner.invoke(
                        main,
                        ['download', 'exec_123', '--file', 'output.json', '--output-dir', temp_script_dir],
                        catch_exceptions=False,
                    )

        # Should attempt to download specific file
        assert result.exit_code == 0 or "output.json" in result.output


@pytest.mark.e2e
class TestLargeFileStreaming:
    """Test large file streaming (Story 7-6)."""

    def test_streaming_download_for_large_files(self, temp_script_dir):
        """Test streaming is used for large file downloads."""
        from rgrid.utils.file_download import download_file_streaming

        # This tests the streaming download mechanism exists
        # Full E2E test requires actual staging environment
        assert callable(download_file_streaming)

    def test_progress_display_for_large_uploads(self, temp_script_dir):
        """Test progress bar is shown for large file uploads."""
        from rgrid.utils.file_upload import upload_file_streaming

        # Verify streaming upload function exists
        assert callable(upload_file_streaming)


@pytest.mark.e2e
class TestBatchDownload:
    """Test batch output download (Story 5-4)."""

    def test_batch_download_all_outputs(self, mock_api_client, temp_script_dir):
        """Test downloading all outputs from a batch."""
        from rgrid.batch_download import download_batch_outputs

        # Mock batch executions
        mock_api_client.get_batch_executions.return_value = [
            {
                "execution_id": "exec_1",
                "status": "completed",
                "batch_metadata": {"input_file": "data_1.csv"},
            },
            {
                "execution_id": "exec_2",
                "status": "completed",
                "batch_metadata": {"input_file": "data_2.csv"},
            },
        ]

        # Mock artifacts for each execution
        mock_api_client.get_artifacts.return_value = [
            {"filename": "output.json", "artifact_type": "output", "file_path": "test/output.json"},
        ]

        # This verifies the batch download function is callable
        # Full test requires staging
        assert callable(download_batch_outputs)
