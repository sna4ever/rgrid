"""Unit tests for file handling (Tier 4 - Story 2-5).

Tests cover:
- CLI file argument detection
- MinIO presigned URL generation
- File upload logic
- Runner file download logic
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestFileArgumentDetection:
    """Test CLI detection of file vs string arguments."""

    def test_detect_file_arguments_with_existing_file(self):
        """When argument is an existing file path, should detect it as file."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            temp_file = f.name

        try:
            from rgrid.utils.file_detection import detect_file_arguments

            args = ['script.py', temp_file, '--flag', 'value']

            # Act
            file_args, regular_args = detect_file_arguments(args)

            # Assert
            assert temp_file in file_args, "Existing file should be detected"
            assert '--flag' in regular_args
            assert 'value' in regular_args
        finally:
            os.unlink(temp_file)

    def test_detect_file_arguments_with_string_arg(self):
        """When argument is a string (not file path), should treat as regular arg."""
        from rgrid.utils.file_detection import detect_file_arguments

        # Arrange
        args = ['script.py', 'some_string', '--flag', 'value']

        # Act
        file_args, regular_args = detect_file_arguments(args)

        # Assert
        assert len(file_args) == 0, "Non-existent paths should not be detected as files"
        assert 'some_string' in regular_args

    def test_detect_multiple_file_arguments(self):
        """When multiple file arguments exist, should detect all."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f1, \
             tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f2:
            f1.write('{"test": "data1"}')
            f2.write('col1,col2\n1,2')
            file1 = f1.name
            file2 = f2.name

        try:
            from rgrid.utils.file_detection import detect_file_arguments

            args = ['script.py', file1, 'regular_arg', file2]

            # Act
            file_args, regular_args = detect_file_arguments(args)

            # Assert
            assert file1 in file_args
            assert file2 in file_args
            assert len(file_args) == 2
            assert 'regular_arg' in regular_args
        finally:
            os.unlink(file1)
            os.unlink(file2)


class TestPresignedURLGeneration:
    """Test MinIO presigned URL generation for uploads."""

    def test_generate_presigned_put_url(self):
        """MinIO client should generate presigned PUT URL with correct format."""
        from api.app.storage import MinIOClient

        # Arrange
        with patch('api.app.storage.boto3') as mock_boto3:
            mock_client = Mock()
            mock_boto3.client.return_value = mock_client
            # Mock returns URL with the full object key path
            mock_client.generate_presigned_url.return_value = "https://minio:9000/rgrid/executions/exec_123/inputs/test.json?signature=abc123"

            minio = MinIOClient()
            object_key = "executions/exec_123/inputs/test.json"

            # Act
            url = minio.generate_presigned_upload_url(object_key, expiration=3600)

            # Assert
            assert url.startswith("https://")
            assert "rgrid" in url
            assert "exec_123/inputs/test.json" in url
            mock_client.generate_presigned_url.assert_called_once()

    def test_presigned_url_includes_execution_id(self):
        """Presigned URL should include execution ID in path."""
        from api.app.storage import MinIOClient

        # Arrange
        with patch('api.app.storage.boto3') as mock_boto3:
            mock_client = Mock()
            mock_boto3.client.return_value = mock_client
            mock_client.generate_presigned_url.return_value = "https://minio:9000/rgrid/executions/exec_abc/inputs/file.json"

            minio = MinIOClient()
            exec_id = "exec_abc"
            filename = "file.json"
            object_key = f"executions/{exec_id}/inputs/{filename}"

            # Act
            url = minio.generate_presigned_upload_url(object_key)

            # Assert
            assert exec_id in url


class TestFileUpload:
    """Test CLI file upload to MinIO."""

    @patch('httpx.Client.put')
    def test_upload_file_to_presigned_url(self, mock_put):
        """CLI should upload file to presigned URL using PUT request."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            temp_file = f.name

        try:
            from rgrid.utils.file_upload import upload_file_to_minio

            presigned_url = "https://minio:9000/rgrid/test.json?signature=abc"
            mock_put.return_value = Mock(status_code=200)

            # Act
            success = upload_file_to_minio(temp_file, presigned_url)

            # Assert
            assert success is True
            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert call_args[0][0] == presigned_url
        finally:
            os.unlink(temp_file)

    @patch('httpx.Client.put')
    def test_upload_large_file(self, mock_put):
        """CLI should successfully upload files larger than 10MB."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Create 11MB file
            f.write(b'0' * (11 * 1024 * 1024))
            temp_file = f.name

        try:
            from rgrid.utils.file_upload import upload_file_to_minio

            presigned_url = "https://minio:9000/rgrid/large.bin?signature=abc"
            mock_put.return_value = Mock(status_code=200)

            # Act
            success = upload_file_to_minio(temp_file, presigned_url)

            # Assert
            assert success is True
            # Verify file size was correct
            file_size = os.path.getsize(temp_file)
            assert file_size > 10 * 1024 * 1024
        finally:
            os.unlink(temp_file)


class TestRunnerFileDownload:
    """Test runner downloads files from MinIO before execution."""

    @patch('httpx.stream')
    def test_runner_downloads_input_files(self, mock_stream):
        """Runner should download input files to /work directory before execution."""
        from runner.runner.file_handler import download_input_files

        # Arrange
        download_urls = {
            "input.json": "https://minio:9000/rgrid/exec_123/inputs/input.json?signature=abc"
        }
        work_dir = Path(tempfile.mkdtemp())

        # Mock streaming response context manager
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.iter_bytes.return_value = [b'{"test": "data"}']
        mock_stream.return_value.__enter__.return_value = mock_response

        try:
            # Act
            downloaded_files = download_input_files(download_urls, work_dir)

            # Assert
            assert "input.json" in downloaded_files
            downloaded_path = work_dir / "input.json"
            assert downloaded_path.exists()
            assert downloaded_path.read_text() == '{"test": "data"}'
        finally:
            # Cleanup
            if work_dir.exists():
                for file in work_dir.iterdir():
                    file.unlink()
                work_dir.rmdir()

    @patch('httpx.stream')
    def test_runner_downloads_multiple_files(self, mock_stream):
        """Runner should download all input files correctly."""
        from runner.runner.file_handler import download_input_files

        # Arrange
        download_urls = {
            "file1.json": "https://minio:9000/rgrid/exec_123/inputs/file1.json",
            "file2.csv": "https://minio:9000/rgrid/exec_123/inputs/file2.csv",
            "file3.txt": "https://minio:9000/rgrid/exec_123/inputs/file3.txt",
        }
        work_dir = Path(tempfile.mkdtemp())

        def mock_stream_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            if "file1" in url:
                mock_response.iter_bytes.return_value = [b'{"data": 1}']
            elif "file2" in url:
                mock_response.iter_bytes.return_value = [b'col1,col2\n1,2']
            elif "file3" in url:
                mock_response.iter_bytes.return_value = [b'text content']
            # Return context manager
            cm = MagicMock()
            cm.__enter__.return_value = mock_response
            cm.__exit__.return_value = None
            return cm

        mock_stream.side_effect = mock_stream_side_effect

        try:
            # Act
            downloaded_files = download_input_files(download_urls, work_dir)

            # Assert
            assert len(downloaded_files) == 3
            assert (work_dir / "file1.json").exists()
            assert (work_dir / "file2.csv").exists()
            assert (work_dir / "file3.txt").exists()
        finally:
            # Cleanup
            if work_dir.exists():
                for file in work_dir.iterdir():
                    file.unlink()
                work_dir.rmdir()

    def test_runner_maps_args_to_container_paths(self):
        """Runner should replace file paths with /work paths in arguments."""
        from runner.runner.file_handler import map_args_to_container_paths

        # Arrange
        original_args = ['input.json', '--output', 'result.txt', 'regular_arg']
        input_files = ['input.json']

        # Act
        container_args = map_args_to_container_paths(original_args, input_files)

        # Assert
        assert '/work/input.json' in container_args
        assert '--output' in container_args
        assert 'result.txt' in container_args
        assert 'regular_arg' in container_args
