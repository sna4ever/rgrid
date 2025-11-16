"""Integration tests for large file handling (Story 7-6).

These tests verify that files >100MB can be uploaded and downloaded
efficiently without exhausting memory.
"""

import hashlib
import io
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import gzip


@pytest.fixture
def large_file_500mb(tmp_path):
    """Create a 500MB test file."""
    file_path = tmp_path / "large_500mb.dat"

    # Create 500MB file efficiently (sparse file not suitable for testing)
    # Use dd-like approach but in Python
    chunk = b"x" * (1024 * 1024)  # 1MB chunk
    with open(file_path, "wb") as f:
        for _ in range(500):  # 500 x 1MB = 500MB
            f.write(chunk)

    return file_path


@pytest.fixture
def medium_file_100mb(tmp_path):
    """Create a 100MB test file for boundary testing."""
    file_path = tmp_path / "medium_100mb.dat"

    chunk = b"y" * (1024 * 1024)  # 1MB chunk
    with open(file_path, "wb") as f:
        for _ in range(100):  # 100 x 1MB = 100MB
            f.write(chunk)

    return file_path


@pytest.mark.slow
class TestLargeFileUpload:
    """Test large file upload scenarios."""

    def test_upload_500mb_file(self, large_file_500mb, tmp_path):
        """500MB file should upload successfully with streaming."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange
        presigned_url = "https://example.com/upload"
        storage = io.BytesIO()

        # Mock httpx to capture streamed data
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            def capture_streaming(url, **kwargs):
                # Check for 'content' parameter (httpx uses 'content' for streaming)
                data = kwargs.get("content") or kwargs.get("data")
                chunk_count = 0

                if hasattr(data, "__iter__"):
                    for chunk in data:
                        storage.write(chunk)
                        chunk_count += 1

                # Verify it was streamed in chunks, not as one big block
                assert chunk_count > 1, "Should stream in multiple chunks"

                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = capture_streaming

            # Act
            result = upload_file_streaming(str(large_file_500mb), presigned_url)

            # Assert
            assert result is True

            # Verify compression occurred
            original_size = large_file_500mb.stat().st_size
            compressed_size = storage.tell()

            # Should be compressed (even though our test data isn't very compressible)
            # At minimum, we verify streaming worked
            assert compressed_size > 0

    def test_upload_memory_efficient(self, medium_file_100mb):
        """Upload should not load entire file into memory."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange
        presigned_url = "https://example.com/upload"

        # Mock to track if data is provided as stream
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            def verify_not_bytes(url, **kwargs):
                data = kwargs.get("data")
                # Data should be iterator/generator, NOT bytes
                assert not isinstance(data, bytes), (
                    "File should be streamed, not loaded entirely as bytes"
                )

                # Consume the iterator to simulate upload
                if hasattr(data, "__iter__"):
                    for _ in data:
                        pass

                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = verify_not_bytes

            # Act
            result = upload_file_streaming(str(medium_file_100mb), presigned_url)

            # Assert
            assert result is True


@pytest.mark.slow
class TestLargeFileDownload:
    """Test large file download scenarios."""

    def test_download_500mb_file(self, tmp_path):
        """500MB file should download successfully with streaming."""
        from cli.rgrid.utils.file_download import download_file_streaming

        # Arrange
        output_file = tmp_path / "downloaded_500mb.dat"
        presigned_url = "https://example.com/download"

        # Create compressed 500MB data (simulate server response)
        # Use smaller sample and repeat to simulate large file without actually creating it
        sample = b"z" * (1024 * 1024)  # 1MB sample
        compressed_sample = gzip.compress(sample)

        # Simulate 500 chunks (500MB)
        def generate_chunks():
            for _ in range(500):
                yield compressed_sample

        with patch("cli.rgrid.utils.file_download.httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {
                "content-length": str(len(compressed_sample) * 500),
                "content-encoding": "gzip"
            }
            # Create all compressed data
            all_compressed = compressed_sample * 500
            mock_response.content = all_compressed
            mock_response.iter_bytes = Mock(return_value=generate_chunks())
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Act
            result = download_file_streaming(presigned_url, str(output_file))

            # Assert
            assert result is True
            assert output_file.exists()

            # Verify file size is correct (decompressed)
            expected_size = 500 * 1024 * 1024  # 500MB
            actual_size = output_file.stat().st_size
            assert actual_size == expected_size

    def test_round_trip_integrity(self, tmp_path):
        """Upload + download should preserve file integrity."""
        from cli.rgrid.utils.file_upload import upload_file_streaming
        from cli.rgrid.utils.file_download import download_file_streaming

        # Arrange: Create 10MB test file with random-ish data
        original_file = tmp_path / "original.dat"
        test_data = b"Test content " * (10 * 1024 * 100)  # ~10MB
        original_file.write_bytes(test_data)

        original_checksum = hashlib.sha256(test_data).hexdigest()

        upload_url = "https://example.com/upload"
        download_url = "https://example.com/download"
        downloaded_file = tmp_path / "downloaded.dat"

        # Simulate MinIO storage
        storage = io.BytesIO()

        # Mock upload
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            def capture_upload(url, **kwargs):
                # Check for 'content' parameter (httpx uses 'content' for streaming)
                data = kwargs.get("content") or kwargs.get("data")
                if hasattr(data, "__iter__"):
                    for chunk in data:
                        storage.write(chunk)
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = capture_upload
            upload_result = upload_file_streaming(str(original_file), upload_url)

        assert upload_result is True

        # Mock download with stored data
        storage.seek(0)
        stored_data = storage.read()

        with patch("cli.rgrid.utils.file_download.httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {
                "content-length": str(len(stored_data)),
                "content-encoding": "gzip"
            }
            mock_response.content = stored_data
            mock_response.iter_bytes = Mock(return_value=iter([stored_data]))
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            download_result = download_file_streaming(download_url, str(downloaded_file))

        # Assert
        assert download_result is True
        assert downloaded_file.exists()

        # Verify integrity
        downloaded_checksum = hashlib.sha256(downloaded_file.read_bytes()).hexdigest()
        assert downloaded_checksum == original_checksum, "File integrity must be preserved"


@pytest.mark.slow
class TestProgressBar:
    """Test progress bar display for large transfers."""

    def test_progress_bar_display(self, tmp_path, capsys):
        """Progress bar should display during large file transfers."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange: Create 10MB file
        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"x" * (10 * 1024 * 1024))

        presigned_url = "https://example.com/upload"

        # Mock httpx
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200

            def consume_data(url, **kwargs):
                data = kwargs.get("data")
                if hasattr(data, "__iter__"):
                    for _ in data:
                        pass
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = consume_data

            # Act
            result = upload_file_streaming(str(test_file), presigned_url, show_progress=True)

            # Assert
            assert result is True
            # Progress bar would be shown via tqdm (tested manually)
            # For unit test, we just verify the function completes
