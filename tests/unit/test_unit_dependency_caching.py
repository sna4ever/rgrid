"""Unit tests for dependency layer caching (Tier 5 - Story 6-2)."""

import pytest
import hashlib
from unittest.mock import Mock, patch


# Import will fail until we implement - that's expected in TDD
try:
    from runner.runner.cache import calculate_deps_hash, lookup_dependency_cache, store_dependency_cache
except ImportError:
    # Mock these for now - tests will fail until implemented
    calculate_deps_hash = None
    lookup_dependency_cache = None
    store_dependency_cache = None


class TestDependencyHashCalculation:
    """Test the dependency hash calculation logic."""

    def test_deps_hash_calculation(self):
        """SHA256 hash should be consistent for same requirements.txt content."""
        # Arrange
        requirements_content = "numpy==1.24.0\npandas==2.0.0\nrequests==2.28.0"

        # Act
        hash1 = calculate_deps_hash(requirements_content)
        hash2 = calculate_deps_hash(requirements_content)

        # Assert
        assert hash1 == hash2, "Same requirements.txt should produce same hash"
        assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"
        assert isinstance(hash1, str), "Hash should be a string"

    def test_hash_changes_on_modification(self):
        """Modified requirements.txt should produce different hash."""
        # Arrange
        original = "numpy==1.24.0\npandas==2.0.0"
        modified = "numpy==1.24.0\npandas==2.0.1"  # Version changed

        # Act
        hash_original = calculate_deps_hash(original)
        hash_modified = calculate_deps_hash(modified)

        # Assert
        assert hash_original != hash_modified, "Different requirements.txt should produce different hash"

    def test_hash_same_for_reordered_dependencies(self):
        """Same dependencies in different order should produce same hash (normalized)."""
        # Arrange
        order1 = "pandas==2.0.0\nnumpy==1.24.0\nrequests==2.28.0"
        order2 = "numpy==1.24.0\nrequests==2.28.0\npandas==2.0.0"

        # Act
        hash1 = calculate_deps_hash(order1)
        hash2 = calculate_deps_hash(order2)

        # Assert
        assert hash1 == hash2, "Reordered dependencies should produce same hash (normalized)"

    def test_empty_requirements_hash(self):
        """Empty requirements.txt should produce valid hash."""
        # Arrange
        empty_content = ""

        # Act
        hash_result = calculate_deps_hash(empty_content)

        # Assert
        assert len(hash_result) == 64, "Empty requirements should still produce valid hash"
        assert isinstance(hash_result, str), "Hash should be a string"


class TestDependencyCacheLookup:
    """Test cache lookup functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_cache_lookup_hit(self, mock_db):
        """Find existing dependency cache entry."""
        # Arrange
        deps_hash = "abc123" * 10 + "abcd"  # 64 char hash
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("layer_abc123",)
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_dependency_cache(deps_hash)

        # Assert
        assert result == "layer_abc123", "Should return docker layer ID on cache hit"

    @patch('runner.runner.cache.get_db_connection')
    def test_cache_miss(self, mock_db):
        """Return None when deps_hash not found."""
        # Arrange
        deps_hash = "xyz789" * 10 + "wxyz"  # 64 char hash
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        result = lookup_dependency_cache(deps_hash)

        # Assert
        assert result is None, "Should return None when cache miss"


class TestDependencyCacheStorage:
    """Test cache storage functionality."""

    @patch('runner.runner.cache.get_db_connection')
    def test_store_dependency_cache(self, mock_db):
        """Store new dependency cache entry."""
        # Arrange
        deps_hash = "def456" * 10 + "defg"  # 64 char hash
        docker_layer_id = "sha256:layer123456"
        requirements_content = "numpy==1.24.0\npandas==2.0.0"
        mock_cursor = Mock()
        mock_db.return_value.cursor.return_value = mock_cursor

        # Act
        store_dependency_cache(deps_hash, docker_layer_id, requirements_content)

        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT" in call_args[0][0].upper(), "Should execute INSERT statement"
        # call_args[0] is (sql_string, params_tuple)
        assert deps_hash in call_args[0][1], "Should include deps_hash in INSERT parameters"


class TestCacheInvalidationScenarios:
    """Critical test cases for cache invalidation."""

    def test_add_dependency_invalidates_cache(self):
        """Adding a dependency to requirements.txt should produce new hash."""
        # Arrange
        original = "numpy==1.24.0"
        with_addition = "numpy==1.24.0\npandas==2.0.0"

        # Act
        hash_original = calculate_deps_hash(original)
        hash_with_addition = calculate_deps_hash(with_addition)

        # Assert
        assert hash_original != hash_with_addition, "Adding dependency should invalidate cache"

    def test_remove_dependency_invalidates_cache(self):
        """Removing a dependency from requirements.txt should produce new hash."""
        # Arrange
        original = "numpy==1.24.0\npandas==2.0.0"
        after_removal = "numpy==1.24.0"

        # Act
        hash_original = calculate_deps_hash(original)
        hash_after_removal = calculate_deps_hash(after_removal)

        # Assert
        assert hash_original != hash_after_removal, "Removing dependency should invalidate cache"

    def test_change_version_invalidates_cache(self):
        """Changing version of a dependency should produce new hash."""
        # Arrange
        version1 = "numpy==1.20.0"
        version2 = "numpy==1.21.0"

        # Act
        hash_v1 = calculate_deps_hash(version1)
        hash_v2 = calculate_deps_hash(version2)

        # Assert
        assert hash_v1 != hash_v2, "Version change should invalidate cache"

    def test_whitespace_normalized(self):
        """Extra whitespace should not affect hash (normalized)."""
        # Arrange
        clean = "numpy==1.24.0\npandas==2.0.0"
        with_whitespace = "numpy==1.24.0  \n  pandas==2.0.0\n\n"

        # Act
        hash_clean = calculate_deps_hash(clean)
        hash_whitespace = calculate_deps_hash(with_whitespace)

        # Assert
        assert hash_clean == hash_whitespace, "Whitespace differences should be normalized"
