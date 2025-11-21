"""Unit tests for script content hashing and cache lookup (Tier 5 - Story 6-1).

This story implements:
- SHA256 hashing of script content
- Script cache lookup (script_hash + runtime -> docker_image_id)
- Script cache storage after building new images

AC-6.1:
1. When execution is submitted, API calculates SHA256 hash of script content
2. API checks script_cache table for existing hash + runtime
3. If cache hit, execution uses cached Docker image (no build)
4. If cache miss, runner builds new image and stores in cache
"""

import pytest
import hashlib
from unittest.mock import Mock, patch


# Import will fail until we implement - that's expected in TDD
try:
    from runner.runner.cache import (
        calculate_script_hash,
        lookup_script_cache,
        store_script_cache,
    )
except ImportError:
    # Mock these for now - tests will fail until implemented
    calculate_script_hash = None
    lookup_script_cache = None
    store_script_cache = None


class TestScriptHashCalculation:
    """Test the script content hash calculation logic."""

    def test_script_hash_calculation_deterministic(self):
        """SHA256 hash should be consistent for same script content."""
        # Arrange
        script_content = "print('Hello, World!')"

        # Act
        hash1 = calculate_script_hash(script_content)
        hash2 = calculate_script_hash(script_content)

        # Assert
        assert hash1 == hash2, "Same script content should produce same hash"
        assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"
        assert isinstance(hash1, str), "Hash should be a string"

    def test_script_hash_changes_on_modification(self):
        """Modified script should produce different hash."""
        # Arrange
        original = "print('Hello')"
        modified = "print('Hello, World!')"

        # Act
        hash_original = calculate_script_hash(original)
        hash_modified = calculate_script_hash(modified)

        # Assert
        assert hash_original != hash_modified, "Different scripts should produce different hash"

    def test_script_hash_whitespace_sensitive(self):
        """Script hash should be sensitive to whitespace changes (unlike deps hash).

        This is intentional - script whitespace can affect behavior (Python indentation).
        """
        # Arrange
        original = "print('test')"
        with_space = "print('test') "  # Extra space at end

        # Act
        hash_original = calculate_script_hash(original)
        hash_with_space = calculate_script_hash(with_space)

        # Assert
        assert hash_original != hash_with_space, "Whitespace changes should produce different hash"

    def test_script_hash_empty_content(self):
        """Empty script should produce valid hash."""
        # Arrange
        empty_content = ""

        # Act
        hash_result = calculate_script_hash(empty_content)

        # Assert
        assert len(hash_result) == 64, "Empty script should still produce valid hash"
        assert isinstance(hash_result, str), "Hash should be a string"

    def test_script_hash_matches_manual_sha256(self):
        """Verify hash matches standard SHA256 implementation."""
        # Arrange
        script_content = "x = 1 + 2"
        expected_hash = hashlib.sha256(script_content.encode('utf-8')).hexdigest()

        # Act
        actual_hash = calculate_script_hash(script_content)

        # Assert
        assert actual_hash == expected_hash, "Hash should match standard SHA256"

    def test_script_hash_multiline_script(self):
        """Test hash calculation for multiline scripts."""
        # Arrange
        multiline_script = """
import os
import sys

def main():
    print('Hello')
    return 0

if __name__ == '__main__':
    main()
"""

        # Act
        hash1 = calculate_script_hash(multiline_script)
        hash2 = calculate_script_hash(multiline_script)

        # Assert
        assert hash1 == hash2, "Multiline script should produce consistent hash"
        assert len(hash1) == 64, "Should be valid SHA256 hash"

    def test_script_hash_unicode_content(self):
        """Test hash calculation with unicode characters."""
        # Arrange
        unicode_script = "print('Hello, World!')"

        # Act
        hash_result = calculate_script_hash(unicode_script)

        # Assert
        assert len(hash_result) == 64, "Unicode script should produce valid hash"


class TestScriptCacheLookup:
    """Test script cache lookup functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_script_cache_lookup_hit(self, mock_db):
        """Find existing script cache entry."""
        # Arrange
        script_hash = "abc123" * 10 + "abcd"  # 64 char hash
        runtime = "python:3.11"
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("sha256:image123",)
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_script_cache(script_hash, runtime)

        # Assert
        assert result == "sha256:image123", "Should return docker image ID on cache hit"

    @patch('runner.runner.cache.get_db_connection')
    def test_script_cache_miss(self, mock_db):
        """Return None when script_hash not found."""
        # Arrange
        script_hash = "xyz789" * 10 + "wxyz"  # 64 char hash
        runtime = "python:3.11"
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_script_cache(script_hash, runtime)

        # Assert
        assert result is None, "Should return None when cache miss"

    @patch('runner.runner.cache.get_db_connection')
    def test_script_cache_runtime_specific(self, mock_db):
        """Different runtimes should be treated as different cache entries."""
        # Arrange
        script_hash = "abc123" * 10 + "abcd"
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # No match for different runtime
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_script_cache(script_hash, "python:3.12")  # Different runtime

        # Assert
        # Verify SQL includes runtime parameter
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert "runtime" in sql.lower(), "Query should filter by runtime"
        assert "python:3.12" in params, "Runtime should be in query params"

    @patch('runner.runner.cache.get_db_connection')
    def test_script_cache_db_error_returns_none(self, mock_db):
        """Database errors should return None (graceful degradation)."""
        # Arrange
        mock_db.side_effect = Exception("Database connection failed")

        # Act
        result = lookup_script_cache("abc123" * 10 + "abcd", "python:3.11")

        # Assert
        assert result is None, "Should return None on database error (cache miss)"


class TestScriptCacheStorage:
    """Test script cache storage functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_store_script_cache(self, mock_db):
        """Store new script cache entry."""
        # Arrange
        script_hash = "def456" * 10 + "defg"  # 64 char hash
        runtime = "python:3.11"
        docker_image_id = "sha256:newimage123456"
        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_script_cache(script_hash, runtime, docker_image_id)

        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "INSERT" in sql.upper(), "Should execute INSERT statement"
        assert script_hash in params, "Should include script_hash in INSERT"
        assert runtime in params, "Should include runtime in INSERT"
        assert docker_image_id in params, "Should include docker_image_id in INSERT"

    @patch('runner.runner.cache.get_db_connection')
    def test_store_script_cache_upsert(self, mock_db):
        """Storage should handle duplicate entries gracefully (upsert)."""
        # Arrange
        script_hash = "def456" * 10 + "defg"
        runtime = "python:3.11"
        docker_image_id = "sha256:newimage123456"
        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_script_cache(script_hash, runtime, docker_image_id)

        # Assert
        sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql.upper(), "Should use upsert pattern (ON CONFLICT)"


class TestScriptCacheInvalidation:
    """Test automatic cache invalidation scenarios."""

    def test_any_change_invalidates_cache(self):
        """Any change to script content should produce new hash."""
        # Arrange
        original = "print('hello')"
        variations = [
            "print('Hello')",      # Case change
            "print('hello') ",     # Trailing space
            " print('hello')",     # Leading space
            "print('hello')\n",    # Trailing newline
            "print('helo')",       # Typo fix
            "# comment\nprint('hello')",  # Added comment
        ]

        # Act
        original_hash = calculate_script_hash(original)

        # Assert
        for variation in variations:
            variation_hash = calculate_script_hash(variation)
            assert original_hash != variation_hash, (
                f"Variation '{variation[:20]}...' should produce different hash"
            )

    def test_revert_produces_same_hash(self):
        """Reverting to original script should produce original hash (cache hit)."""
        # Arrange
        original = "print('version 1')"
        modified = "print('version 2')"

        # Act
        hash_v1 = calculate_script_hash(original)
        hash_v2 = calculate_script_hash(modified)
        hash_reverted = calculate_script_hash(original)  # Back to v1

        # Assert
        assert hash_v1 != hash_v2, "Different versions should have different hashes"
        assert hash_v1 == hash_reverted, "Reverting should produce same hash as original"
