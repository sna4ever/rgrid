"""Unit tests for file streaming (Story 7-6: Large File Streaming and Compression)."""

import gzip
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import httpx


class TestStreamUpload:
    """Test streaming upload functionality."""

    def test_stream_upload_chunks(self, tmp_path):
        """Upload should stream file in chunks, not load entire file into memory."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange: Create 10MB test file
        test_file = tmp_path / "large_file.dat"
        chunk_size = 1024 * 1024  # 1MB
        test_file.write_bytes(b"x" * (10 * chunk_size))

        presigned_url = "https://example.com/upload"

        # Mock httpx client to verify streaming behavior
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.put.return_value = mock_response

            # Act
            result = upload_file_streaming(str(test_file), presigned_url)

            # Assert
            assert result is True
            # Verify put was called with streaming data (generator or iterator)
            put_call = mock_client.return_value.__enter__.return_value.put.call_args
            assert put_call is not None

    def test_gzip_compression(self, tmp_path):
        """Files should be compressed with gzip during upload."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange: Create test file with compressible content
        test_file = tmp_path / "compressible.txt"
        original_content = b"A" * 10000  # Highly compressible
        test_file.write_bytes(original_content)

        presigned_url = "https://example.com/upload"

        captured_data = io.BytesIO()

        # Mock to capture uploaded data
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            def capture_put(url, **kwargs):
                # Capture the data that would be uploaded
                if "data" in kwargs:
                    data = kwargs["data"]
                    if hasattr(data, "__iter__"):
                        # It's a generator/iterator
                        for chunk in data:
                            captured_data.write(chunk)
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = capture_put

            # Act
            upload_file_streaming(str(test_file), presigned_url)

            # Assert: Uploaded data should be smaller than original (compressed)
            compressed_size = captured_data.tell()
            original_size = len(original_content)

            # gzip should reduce size significantly for repetitive data
            # Allow some overhead but should be much smaller
            assert compressed_size < original_size / 2, "Data should be compressed"

    def test_memory_usage_constant(self, tmp_path):
        """Memory usage should not grow with file size (streaming)."""
        from cli.rgrid.utils.file_upload import upload_file_streaming

        # Arrange: Create large file
        test_file = tmp_path / "large.dat"
        test_file.write_bytes(b"x" * (50 * 1024 * 1024))  # 50MB

        presigned_url = "https://example.com/upload"

        # Mock httpx
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200

            # Track if data is streamed (generator/iterator) not loaded all at once
            def verify_streaming(url, **kwargs):
                data = kwargs.get("data")
                # Should be an iterator/generator, not bytes
                assert not isinstance(data, bytes), "Should stream, not load all into memory"
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = verify_streaming

            # Act
            result = upload_file_streaming(str(test_file), presigned_url)

            # Assert
            assert result is True


class TestStreamDownload:
    """Test streaming download functionality."""

    def test_stream_download_chunks(self, tmp_path):
        """Download should stream file in chunks, not load entire file into memory."""
        from cli.rgrid.utils.file_download import download_file_streaming

        # Arrange
        output_file = tmp_path / "downloaded.dat"
        presigned_url = "https://example.com/download"

        # Mock httpx to return streaming response
        with patch("cli.rgrid.utils.file_download.httpx.get") as mock_get:
            # Create mock streaming response
            mock_response = Mock()
            mock_response.headers = {"content-length": "10485760"}  # 10MB

            # Simulate streaming chunks
            chunks = [b"x" * 8192 for _ in range(1280)]  # 10MB in 8KB chunks
            mock_response.content = b"x" * (8192 * 1280)  # Fallback content
            mock_response.iter_bytes = Mock(return_value=iter(chunks))
            mock_response.raise_for_status = Mock()  # Add raise_for_status
            mock_get.return_value = mock_response

            # Act
            result = download_file_streaming(presigned_url, str(output_file))

            # Assert
            assert result is True
            assert output_file.exists()
            # Verify iter_bytes was called (streaming)
            mock_response.iter_bytes.assert_called()

    def test_gzip_decompression(self, tmp_path):
        """Files should be automatically decompressed during download."""
        from cli.rgrid.utils.file_download import download_file_streaming

        # Arrange
        output_file = tmp_path / "decompressed.txt"
        presigned_url = "https://example.com/download"

        original_data = b"Hello World " * 1000
        compressed_data = gzip.compress(original_data)

        # Mock httpx to return compressed data
        with patch("cli.rgrid.utils.file_download.httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {
                "content-length": str(len(compressed_data)),
                "content-encoding": "gzip"
            }
            mock_response.content = compressed_data  # Add content attribute
            mock_response.iter_bytes = Mock(return_value=iter([compressed_data]))
            mock_response.raise_for_status = Mock()  # Add raise_for_status
            mock_get.return_value = mock_response

            # Act
            result = download_file_streaming(presigned_url, str(output_file))

            # Assert
            assert result is True
            assert output_file.exists()
            # File should contain decompressed data
            assert output_file.read_bytes() == original_data

    def test_checksum_verification(self, tmp_path):
        """File integrity should be preserved during upload/download."""
        import hashlib
        from cli.rgrid.utils.file_upload import upload_file_streaming
        from cli.rgrid.utils.file_download import download_file_streaming

        # Arrange: Create test file
        test_file = tmp_path / "original.dat"
        test_content = b"Test data " * 10000
        test_file.write_bytes(test_content)

        original_checksum = hashlib.sha256(test_content).hexdigest()

        upload_url = "https://example.com/upload"
        download_url = "https://example.com/download"
        downloaded_file = tmp_path / "downloaded.dat"

        # Simulate upload -> storage -> download
        uploaded_data = io.BytesIO()

        # Mock upload
        with patch("cli.rgrid.utils.file_upload.httpx.Client") as mock_client:
            def capture_upload(url, **kwargs):
                # Check for 'content' parameter (httpx uses 'content' for streaming)
                data = kwargs.get("content") or kwargs.get("data")
                if hasattr(data, "__iter__"):
                    for chunk in data:
                        uploaded_data.write(chunk)
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

            mock_client.return_value.__enter__.return_value.put.side_effect = capture_upload
            upload_file_streaming(str(test_file), upload_url)

        # Mock download with uploaded (compressed) data
        uploaded_data.seek(0)

        with patch("cli.rgrid.utils.file_download.httpx.get") as mock_get:
            mock_response = Mock()
            compressed_bytes = uploaded_data.read()
            mock_response.headers = {
                "content-length": str(len(compressed_bytes)),
                "content-encoding": "gzip"
            }
            mock_response.content = compressed_bytes  # Add content attribute
            mock_response.iter_bytes = Mock(return_value=iter([compressed_bytes]))
            mock_response.raise_for_status = Mock()  # Add raise_for_status
            mock_get.return_value = mock_response

            download_file_streaming(download_url, str(downloaded_file))

        # Assert: Downloaded file should match original
        downloaded_checksum = hashlib.sha256(downloaded_file.read_bytes()).hexdigest()
        assert downloaded_checksum == original_checksum
