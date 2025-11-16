"""Unit tests for automatic cache invalidation (Tier 5 - Story 6-3).

CRITICAL: Cache invalidation bugs cause data corruption. This test suite
validates that cache automatically invalidates on ANY change to:
- Script content
- Requirements.txt
- Runtime

All tests must pass before Story 6-3 is considered complete.
"""

import pytest
from unittest.mock import Mock, patch


# Import will fail until we implement - expected in TDD
try:
    from runner.runner.cache import (
        calculate_combined_hash,
        lookup_combined_cache,
        store_combined_cache,
    )
except ImportError:
    calculate_combined_hash = None
    lookup_combined_cache = None
    store_combined_cache = None


class TestCombinedHashCalculation:
    """Test combined hash calculation for script + deps + runtime."""

    def test_combined_hash_includes_all_inputs(self):
        """Combined hash should include script, requirements, and runtime."""
        # Arrange
        script = "print('hello')"
        requirements = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash1 = calculate_combined_hash(script, requirements, runtime)

        # Assert
        assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"
        assert isinstance(hash1, str), "Hash should be a string"

    def test_script_content_change_invalidates(self):
        """Modifying script content should produce different hash."""
        # Arrange
        script_v1 = "print('hello')"
        script_v2 = "print('goodbye')"  # Changed
        requirements = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, requirements, runtime)
        hash_v2 = calculate_combined_hash(script_v2, requirements, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Script change should invalidate cache"

    def test_deps_change_invalidates(self):
        """Modifying requirements.txt should produce different hash."""
        # Arrange
        script = "print('hello')"
        requirements_v1 = "numpy==1.24.0"
        requirements_v2 = "numpy==1.24.0\npandas==2.0.0"  # Added dependency
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script, requirements_v1, runtime)
        hash_v2 = calculate_combined_hash(script, requirements_v2, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Dependency change should invalidate cache"

    def test_runtime_change_invalidates(self):
        """Changing runtime should produce different hash."""
        # Arrange
        script = "print('hello')"
        requirements = "numpy==1.24.0"
        runtime_v1 = "python:3.11"
        runtime_v2 = "python:3.12"  # Changed runtime

        # Act
        hash_v1 = calculate_combined_hash(script, requirements, runtime_v1)
        hash_v2 = calculate_combined_hash(script, requirements, runtime_v2)

        # Assert
        assert hash_v1 != hash_v2, "Runtime change should invalidate cache"

    def test_cache_hit_after_revert(self):
        """Reverting changes should produce original hash (cache hit)."""
        # Arrange
        script_v1 = "print('hello')"
        script_v2 = "print('goodbye')"
        requirements = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, requirements, runtime)
        hash_v2 = calculate_combined_hash(script_v2, requirements, runtime)
        hash_v1_reverted = calculate_combined_hash(script_v1, requirements, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Change should produce different hash"
        assert hash_v1 == hash_v1_reverted, "Revert should produce original hash (cache hit)"


class TestCacheLookupAndStorage:
    """Test cache lookup and storage operations."""

    @patch('runner.runner.cache.get_db_connection')
    def test_cache_lookup_returns_existing_entry(self, mock_db):
        """Lookup should return cached image if hash exists."""
        # Arrange
        combined_hash = "abc123" * 10 + "abcd"  # 64 chars
        cached_image = "rgrid-cached:abc123def456"

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (cached_image,)
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_combined_cache(combined_hash)

        # Assert
        assert result == cached_image, "Should return cached image on hit"

    @patch('runner.runner.cache.get_db_connection')
    def test_cache_lookup_returns_none_on_miss(self, mock_db):
        """Lookup should return None if hash not in cache."""
        # Arrange
        combined_hash = "xyz789" * 10 + "wxyz"  # 64 chars

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_combined_cache(combined_hash)

        # Assert
        assert result is None, "Should return None on cache miss"

    @patch('runner.runner.cache.get_db_connection')
    def test_store_combined_cache(self, mock_db):
        """Store should insert new cache entry."""
        # Arrange
        combined_hash = "def456" * 10 + "defg"  # 64 chars
        docker_image_tag = "rgrid-cached:def456ghi789"
        script_content = "print('test')"
        requirements_content = "numpy==1.24.0"
        runtime = "python:3.11"

        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_combined_cache(
            combined_hash, docker_image_tag, script_content,
            requirements_content, runtime
        )

        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT" in call_args[0][0].upper(), "Should execute INSERT statement"

    @patch('runner.runner.cache.get_db_connection')
    def test_old_cache_entries_preserved(self, mock_db):
        """Old cache entries should remain in database."""
        # This test verifies that when we store a new cache entry,
        # old entries are NOT deleted (preserved for historical re-runs)

        # Arrange
        hash_v1 = "abc123" * 10 + "abcd"
        hash_v2 = "xyz789" * 10 + "wxyz"
        image_v1 = "rgrid-cached:v1"
        image_v2 = "rgrid-cached:v2"

        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act - Store v1, then v2
        store_combined_cache(hash_v1, image_v1, "script1", "deps1", "runtime1")
        store_combined_cache(hash_v2, image_v2, "script2", "deps2", "runtime2")

        # Assert - Both inserts should happen (no DELETE statements)
        assert mock_cursor.execute.call_count == 2, "Both entries should be inserted"
        # Check that no DELETE was called
        for call in mock_cursor.execute.call_args_list:
            sql = call[0][0].upper()
            assert "DELETE" not in sql, "Old cache entries should NOT be deleted"


class TestCacheInvalidationMatrix:
    """Critical test matrix for cache invalidation edge cases."""

    def test_1_char_script_change_invalidates(self):
        """Single character change in script should invalidate cache."""
        # Arrange
        script_v1 = "print('hello')"
        script_v2 = "print('helloA')"  # Added 1 char
        requirements = ""
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, requirements, runtime)
        hash_v2 = calculate_combined_hash(script_v2, requirements, runtime)

        # Assert
        assert hash_v1 != hash_v2, "1 character change should invalidate cache"

    def test_whitespace_change_invalidates(self):
        """Whitespace-only change should invalidate cache (no normalization)."""
        # Arrange
        script_v1 = "print('hello')"
        script_v2 = "print('hello') "  # Added trailing space
        requirements = ""
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, requirements, runtime)
        hash_v2 = calculate_combined_hash(script_v2, requirements, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Whitespace change should invalidate cache"

    def test_comment_change_invalidates(self):
        """Comment change should invalidate cache (includes all content)."""
        # Arrange
        script_v1 = "print('hello')"
        script_v2 = "# Comment\nprint('hello')"  # Added comment
        requirements = ""
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, requirements, runtime)
        hash_v2 = calculate_combined_hash(script_v2, requirements, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Comment change should invalidate cache"

    def test_dependency_version_bump_invalidates(self):
        """Changing dependency version should invalidate cache."""
        # Arrange
        script = "import numpy"
        requirements_v1 = "numpy==1.20.0"
        requirements_v2 = "numpy==1.21.0"  # Version bump
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script, requirements_v1, runtime)
        hash_v2 = calculate_combined_hash(script, requirements_v2, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Version bump should invalidate cache"

    def test_dependency_reorder_invalidates(self):
        """Reordering dependencies should invalidate cache."""
        # Note: For Story 6-2, we normalized dependency order.
        # But for combined hash (script + deps), we include deps as-is
        # to catch any change. This is intentional.

        # Arrange
        script = "import numpy"
        requirements_v1 = "numpy==1.24.0\npandas==2.0.0"
        requirements_v2 = "pandas==2.0.0\nnumpy==1.24.0"  # Reordered
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script, requirements_v1, runtime)
        hash_v2 = calculate_combined_hash(script, requirements_v2, runtime)

        # Assert
        # Combined hash should be different (sensitive to order)
        # Even though Story 6-2 normalizes deps for dependency layer caching
        assert hash_v1 != hash_v2, "Reordering deps should invalidate combined cache"

    def test_runtime_version_change_invalidates(self):
        """Changing runtime version should invalidate cache."""
        # Arrange
        script = "print('hello')"
        requirements = ""
        runtime_v1 = "python:3.11"
        runtime_v2 = "python:3.12"  # Minor version change

        # Act
        hash_v1 = calculate_combined_hash(script, requirements, runtime_v1)
        hash_v2 = calculate_combined_hash(script, requirements, runtime_v2)

        # Assert
        assert hash_v1 != hash_v2, "Runtime version change should invalidate cache"

    def test_empty_inputs_produce_valid_hash(self):
        """Empty script/deps should produce valid hash (edge case)."""
        # Arrange
        script = ""
        requirements = ""
        runtime = "python:3.11"

        # Act
        hash_result = calculate_combined_hash(script, requirements, runtime)

        # Assert
        assert len(hash_result) == 64, "Empty inputs should produce valid hash"
