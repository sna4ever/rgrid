"""Unit tests for combined cache invalidation (Story 6-3).

Tests for automatic cache invalidation when any input (script, deps, runtime) changes.
The combined hash approach ensures that ANY change triggers a rebuild.

AC-6.3:
1. When script content changes, new hash is calculated
2. New hash does not match cache → cache miss → rebuild
3. Old cache entry remains valid (for reverting changes)
4. No manual cache clearing required
"""

import pytest
import hashlib
from unittest.mock import Mock, patch


try:
    from runner.runner.cache import (
        calculate_combined_hash,
        lookup_combined_cache,
        store_combined_cache,
        calculate_script_hash,
        calculate_deps_hash,
    )
except ImportError:
    pytest.skip("Cache module not available", allow_module_level=True)


class TestCombinedHashCalculation:
    """Test combined hash calculation for automatic invalidation."""

    def test_combined_hash_is_deterministic(self):
        """Same inputs should produce same hash."""
        # Arrange
        script = "print('hello')"
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash1 = calculate_combined_hash(script, deps, runtime)
        hash2 = calculate_combined_hash(script, deps, runtime)

        # Assert
        assert hash1 == hash2, "Same inputs should produce same hash"
        assert len(hash1) == 64, "Should be valid SHA256 hash"

    def test_script_change_invalidates_cache(self):
        """Changing script should produce different hash (cache invalidation)."""
        # Arrange
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash("print('v1')", deps, runtime)
        hash_v2 = calculate_combined_hash("print('v2')", deps, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Script change should invalidate cache"

    def test_deps_change_invalidates_cache(self):
        """Changing dependencies should produce different hash."""
        # Arrange
        script = "print('test')"
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script, "numpy==1.24.0", runtime)
        hash_v2 = calculate_combined_hash(script, "numpy==1.25.0", runtime)

        # Assert
        assert hash_v1 != hash_v2, "Dependency change should invalidate cache"

    def test_runtime_change_invalidates_cache(self):
        """Changing runtime should produce different hash."""
        # Arrange
        script = "print('test')"
        deps = "numpy==1.24.0"

        # Act
        hash_311 = calculate_combined_hash(script, deps, "python:3.11")
        hash_312 = calculate_combined_hash(script, deps, "python:3.12")

        # Assert
        assert hash_311 != hash_312, "Runtime change should invalidate cache"

    def test_whitespace_in_script_invalidates(self):
        """Script whitespace changes should invalidate cache."""
        # Arrange
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash1 = calculate_combined_hash("print('hi')", deps, runtime)
        hash2 = calculate_combined_hash("print('hi') ", deps, runtime)  # trailing space

        # Assert
        assert hash1 != hash2, "Whitespace in script should invalidate"

    def test_revert_produces_original_hash(self):
        """Reverting to original inputs should produce original hash (cache hit)."""
        # Arrange
        script_v1 = "print('v1')"
        script_v2 = "print('v2')"
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, deps, runtime)
        hash_v2 = calculate_combined_hash(script_v2, deps, runtime)
        hash_reverted = calculate_combined_hash(script_v1, deps, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Different versions should have different hashes"
        assert hash_v1 == hash_reverted, "Reverting should produce original hash"

    def test_empty_deps_produces_valid_hash(self):
        """Empty requirements.txt should produce valid hash."""
        # Arrange
        script = "print('test')"
        empty_deps = ""
        runtime = "python:3.11"

        # Act
        hash_result = calculate_combined_hash(script, empty_deps, runtime)

        # Assert
        assert len(hash_result) == 64, "Empty deps should produce valid hash"

    def test_combined_hash_includes_all_inputs(self):
        """Hash should change when ANY input changes."""
        # Arrange
        base_script = "print('base')"
        base_deps = "numpy==1.24.0"
        base_runtime = "python:3.11"

        base_hash = calculate_combined_hash(base_script, base_deps, base_runtime)

        # Act - Change each input individually
        script_changed = calculate_combined_hash("print('modified')", base_deps, base_runtime)
        deps_changed = calculate_combined_hash(base_script, "pandas==2.0.0", base_runtime)
        runtime_changed = calculate_combined_hash(base_script, base_deps, "python:3.12")

        # Assert - All should be different
        hashes = [base_hash, script_changed, deps_changed, runtime_changed]
        assert len(set(hashes)) == 4, "Each change should produce unique hash"


class TestCombinedCacheLookup:
    """Test combined cache lookup functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_combined_cache_hit(self, mock_db):
        """Cache lookup should return image tag on hit."""
        # Arrange
        combined_hash = "abc123" * 10 + "abcd"
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("rgrid-cached:abc123def456",)
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_combined_cache(combined_hash)

        # Assert
        assert result == "rgrid-cached:abc123def456"

    @patch('runner.runner.cache.get_db_connection')
    def test_combined_cache_miss(self, mock_db):
        """Cache lookup should return None on miss."""
        # Arrange
        combined_hash = "xyz789" * 10 + "wxyz"
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_combined_cache(combined_hash)

        # Assert
        assert result is None

    @patch('runner.runner.cache.get_db_connection')
    def test_cache_graceful_degradation(self, mock_db):
        """Database errors should not crash, return None (cache miss)."""
        # Arrange
        mock_db.side_effect = Exception("Database unavailable")

        # Act
        result = lookup_combined_cache("abc123" * 10 + "abcd")

        # Assert
        assert result is None, "Should return None on error"


class TestCombinedCacheStorage:
    """Test combined cache storage functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_store_combined_cache_entry(self, mock_db):
        """Should store cache entry in database."""
        # Arrange
        combined_hash = "def456" * 10 + "defg"
        image_tag = "rgrid-cached:def456"
        script = "print('test')"
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_combined_cache(combined_hash, image_tag, script, deps, runtime)

        # Assert
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT" in sql.upper()
        assert "combined_cache" in sql.lower()

    @patch('runner.runner.cache.get_db_connection')
    def test_store_uses_upsert(self, mock_db):
        """Should handle duplicate entries gracefully (ON CONFLICT)."""
        # Arrange
        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_combined_cache("hash123" * 8, "tag", "script", "deps", "runtime")

        # Assert
        sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql.upper(), "Should use upsert pattern"


class TestCacheInvalidationScenarios:
    """Test real-world cache invalidation scenarios."""

    def test_add_dependency_invalidates(self):
        """Adding a new dependency should invalidate cache."""
        # Arrange
        script = "import numpy\nprint(numpy.__version__)"
        runtime = "python:3.11"
        deps_v1 = "numpy==1.24.0"
        deps_v2 = "numpy==1.24.0\npandas==2.0.0"  # Added pandas

        # Act
        hash_v1 = calculate_combined_hash(script, deps_v1, runtime)
        hash_v2 = calculate_combined_hash(script, deps_v2, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Adding dependency should invalidate"

    def test_remove_dependency_invalidates(self):
        """Removing a dependency should invalidate cache."""
        # Arrange
        script = "print('test')"
        runtime = "python:3.11"
        deps_v1 = "numpy==1.24.0\npandas==2.0.0"
        deps_v2 = "numpy==1.24.0"  # Removed pandas

        # Act
        hash_v1 = calculate_combined_hash(script, deps_v1, runtime)
        hash_v2 = calculate_combined_hash(script, deps_v2, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Removing dependency should invalidate"

    def test_upgrade_dependency_invalidates(self):
        """Upgrading a dependency version should invalidate cache."""
        # Arrange
        script = "import numpy"
        runtime = "python:3.11"
        deps_v1 = "numpy==1.24.0"
        deps_v2 = "numpy==1.25.0"  # Version upgrade

        # Act
        hash_v1 = calculate_combined_hash(script, deps_v1, runtime)
        hash_v2 = calculate_combined_hash(script, deps_v2, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Version upgrade should invalidate"

    def test_add_comment_to_script_invalidates(self):
        """Adding a comment to script should invalidate (comments affect execution)."""
        # Arrange
        deps = "numpy==1.24.0"
        runtime = "python:3.11"
        script_v1 = "print('test')"
        script_v2 = "# This is a comment\nprint('test')"

        # Act
        hash_v1 = calculate_combined_hash(script_v1, deps, runtime)
        hash_v2 = calculate_combined_hash(script_v2, deps, runtime)

        # Assert
        assert hash_v1 != hash_v2, "Adding comment should invalidate"

    def test_multiple_versions_can_coexist(self):
        """Multiple versions should have unique hashes (can coexist in cache)."""
        # Arrange
        deps = "numpy==1.24.0"
        runtime = "python:3.11"

        versions = [
            "print('v1')",
            "print('v2')",
            "print('v3')",
            "print('v1')",  # Back to v1
        ]

        # Act
        hashes = [calculate_combined_hash(v, deps, runtime) for v in versions]

        # Assert
        assert hashes[0] != hashes[1], "v1 != v2"
        assert hashes[1] != hashes[2], "v2 != v3"
        assert hashes[0] == hashes[3], "v1 == v1 (back to original)"
