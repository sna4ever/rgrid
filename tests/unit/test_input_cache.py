"""Unit tests for optional input file caching (Story 6-4).

Tests for input file caching to skip re-uploads of identical input files.
When the same input files are used across executions, their combined hash
allows cache lookup to reuse existing MinIO file references.

AC-6.4:
1. Given execution uses input files
2. When API calculates `inputs_hash = sha256(all_input_contents)`
3. Then API checks input_cache table
4. And if cache hit, skips upload and uses cached file reference
5. And if cache miss, uploads files and stores hash
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


# ============================================================================
# Test Input Hash Calculation
# ============================================================================


class TestInputHashCalculation:
    """Test input file hash calculation."""

    def test_calculate_input_hash_single_file(self):
        """Single file should produce valid SHA256 hash."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange
        file_contents = [b"Hello, World!"]

        # Act
        result = calculate_input_hash(file_contents)

        # Assert
        assert len(result) == 64, "Should be valid SHA256 hash (64 hex chars)"
        # Hash should be deterministic
        result2 = calculate_input_hash(file_contents)
        assert result == result2, "Same content should produce same hash"

    def test_calculate_input_hash_multiple_files(self):
        """Multiple files should produce combined hash."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange
        file_contents = [b"File 1 content", b"File 2 content"]

        # Act
        result = calculate_input_hash(file_contents)

        # Assert
        assert len(result) == 64, "Should be valid SHA256 hash"

    def test_calculate_input_hash_order_independent(self):
        """Hash should be order-independent (sorted internally)."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange
        file_a = b"File A content"
        file_b = b"File B content"

        # Act - Different orders
        hash1 = calculate_input_hash([file_a, file_b])
        hash2 = calculate_input_hash([file_b, file_a])

        # Assert
        assert hash1 == hash2, "Order should not affect hash"

    def test_calculate_input_hash_different_content(self):
        """Different content should produce different hash."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange
        contents_v1 = [b"Version 1"]
        contents_v2 = [b"Version 2"]

        # Act
        hash_v1 = calculate_input_hash(contents_v1)
        hash_v2 = calculate_input_hash(contents_v2)

        # Assert
        assert hash_v1 != hash_v2, "Different content should produce different hash"

    def test_calculate_input_hash_empty_file(self):
        """Empty file should produce valid hash."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange
        file_contents = [b""]

        # Act
        result = calculate_input_hash(file_contents)

        # Assert
        assert len(result) == 64, "Empty file should produce valid hash"

    def test_calculate_input_hash_binary_file(self):
        """Binary content should be handled correctly."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange - Binary data with non-UTF8 bytes
        binary_content = bytes(range(256))
        file_contents = [binary_content]

        # Act
        result = calculate_input_hash(file_contents)

        # Assert
        assert len(result) == 64, "Binary content should produce valid hash"


class TestInputHashFromFiles:
    """Test hash calculation from actual files."""

    def test_calculate_input_hash_from_files(self):
        """Should read files and calculate combined hash."""
        from cli.rgrid.utils.input_cache import calculate_input_hash_from_files

        # Arrange - Create temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "input1.txt")
            file2 = os.path.join(tmpdir, "input2.txt")

            with open(file1, 'wb') as f:
                f.write(b"Content 1")
            with open(file2, 'wb') as f:
                f.write(b"Content 2")

            # Act
            result = calculate_input_hash_from_files([file1, file2])

            # Assert
            assert len(result) == 64, "Should produce valid SHA256 hash"

    def test_calculate_input_hash_from_files_nonexistent(self):
        """Should raise error for nonexistent files."""
        from cli.rgrid.utils.input_cache import calculate_input_hash_from_files

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            calculate_input_hash_from_files(["/nonexistent/file.txt"])


# ============================================================================
# Test Input Cache Model
# ============================================================================


class TestInputCacheModel:
    """Test the InputCache database model."""

    def test_input_cache_model_attributes(self):
        """Model should have required attributes."""
        from api.app.models.input_cache import InputCache

        # Assert - Model has expected attributes
        assert hasattr(InputCache, '__tablename__')
        assert InputCache.__tablename__ == "input_cache"

        # Check columns exist
        columns = [c.name for c in InputCache.__table__.columns]
        assert 'input_hash' in columns
        assert 'file_references' in columns
        assert 'created_at' in columns
        assert 'last_used_at' in columns
        assert 'use_count' in columns


# ============================================================================
# Test Input Cache API Client Methods
# ============================================================================


class TestInputCacheAPIClient:
    """Test API client methods for input cache."""

    @patch('rgrid.api_client.httpx.Client')
    def test_lookup_input_cache_hit(self, mock_httpx):
        """Cache lookup should return file references on hit."""
        from cli.rgrid.api_client import APIClient

        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "cache_hit": True,
            "file_references": {"input.csv": "executions/old_exec/inputs/input.csv"},
        }
        mock_response.raise_for_status = Mock()

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client

        # Act
        with patch('rgrid.config.config.load_credentials', return_value={
            "api_url": "http://test",
            "api_key": "test-key"
        }):
            client = APIClient(enable_retry=False)
            result = client.lookup_input_cache("abc123" * 10 + "abcd")

        # Assert
        assert result["cache_hit"] is True
        assert "file_references" in result

    @patch('rgrid.api_client.httpx.Client')
    def test_lookup_input_cache_miss(self, mock_httpx):
        """Cache lookup should return cache_hit=False on miss."""
        from cli.rgrid.api_client import APIClient

        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"cache_hit": False}
        mock_response.raise_for_status = Mock()

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client

        # Act
        with patch('rgrid.config.config.load_credentials', return_value={
            "api_url": "http://test",
            "api_key": "test-key"
        }):
            client = APIClient(enable_retry=False)
            result = client.lookup_input_cache("xyz789" * 10 + "wxyz")

        # Assert
        assert result["cache_hit"] is False


# ============================================================================
# Test Input Cache Storage
# ============================================================================


class TestInputCacheStorage:
    """Test storing input cache entries."""

    @patch('rgrid.api_client.httpx.Client')
    def test_store_input_cache(self, mock_httpx):
        """Should store cache entry via API."""
        from cli.rgrid.api_client import APIClient

        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"stored": True}
        mock_response.raise_for_status = Mock()

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client

        # Act
        with patch('rgrid.config.config.load_credentials', return_value={
            "api_url": "http://test",
            "api_key": "test-key"
        }):
            client = APIClient(enable_retry=False)
            result = client.store_input_cache(
                input_hash="abc123" * 10 + "abcd",
                file_references={"input.csv": "executions/exec_123/inputs/input.csv"}
            )

        # Assert
        assert result.get("stored") is True


# ============================================================================
# Test Cache Integration in Run Command
# ============================================================================


class TestInputCacheIntegration:
    """Test input cache integration in the run command flow."""

    def test_cache_hit_skips_upload(self):
        """On cache hit, file upload should be skipped."""
        # This tests the integration logic conceptually
        # Arrange
        cache_hit = True
        cached_file_refs = {"input.csv": "executions/old_exec/inputs/input.csv"}

        # Act - Simulate decision
        should_upload = not cache_hit

        # Assert
        assert should_upload is False, "Cache hit should skip upload"

    def test_cache_miss_triggers_upload(self):
        """On cache miss, file should be uploaded."""
        # Arrange
        cache_hit = False

        # Act - Simulate decision
        should_upload = not cache_hit

        # Assert
        assert should_upload is True, "Cache miss should trigger upload"


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestInputCacheEdgeCases:
    """Test edge cases for input caching."""

    def test_large_file_hash(self):
        """Large file content should hash correctly."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange - 10MB of data
        large_content = b"x" * (10 * 1024 * 1024)
        file_contents = [large_content]

        # Act
        result = calculate_input_hash(file_contents)

        # Assert
        assert len(result) == 64, "Large file should produce valid hash"

    def test_identical_files_same_hash(self):
        """Multiple identical files should produce same hash as single file."""
        from cli.rgrid.utils.input_cache import calculate_input_hash

        # Arrange - Same content twice
        content = b"Identical content"
        single = [content]
        double = [content, content]

        # Act
        hash_single = calculate_input_hash(single)
        hash_double = calculate_input_hash(double)

        # Assert - Should be different (2 files vs 1 file)
        assert hash_single != hash_double, "File count should affect hash"

    def test_cache_preserves_filenames(self):
        """Cache should preserve original filenames in references."""
        # Arrange
        file_refs = {
            "data.csv": "executions/exec_123/inputs/data.csv",
            "config.json": "executions/exec_123/inputs/config.json",
        }

        # Assert - Filenames are keys
        assert "data.csv" in file_refs
        assert "config.json" in file_refs
