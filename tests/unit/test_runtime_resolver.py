"""Unit tests for runtime resolver (Tier 3 - Story 2-3)."""

import pytest
from rgrid_common.runtimes import (
    resolve_runtime,
    get_available_runtimes,
    RUNTIME_MAP,
    DEFAULT_RUNTIME,
)


class TestRuntimeResolver:
    """Test the runtime name to Docker image resolver."""

    def test_none_returns_default_runtime(self):
        """When runtime is None, should return default python:3.11."""
        result = resolve_runtime(None)
        assert result == "python:3.11"
        assert result == DEFAULT_RUNTIME

    def test_short_name_python_resolves_to_default(self):
        """Short name 'python' should resolve to python:3.11."""
        result = resolve_runtime("python")
        assert result == "python:3.11"

    def test_short_name_python312_resolves_correctly(self):
        """Short name 'python3.12' should resolve to python:3.12."""
        result = resolve_runtime("python3.12")
        assert result == "python:3.12"

    def test_short_name_python310_resolves_correctly(self):
        """Short name 'python3.10' should resolve to python:3.10."""
        result = resolve_runtime("python3.10")
        assert result == "python:3.10"

    def test_short_name_node_resolves_to_node20(self):
        """Short name 'node' should resolve to node:20."""
        result = resolve_runtime("node")
        assert result == "node:20"

    def test_short_name_node18_resolves_correctly(self):
        """Short name 'node18' should resolve to node:18."""
        result = resolve_runtime("node18")
        assert result == "node:18"

    def test_full_image_name_passes_through(self):
        """Full image names like 'python:3.11' should pass through unchanged."""
        result = resolve_runtime("python:3.11")
        assert result == "python:3.11"

    def test_unknown_runtime_passes_through(self):
        """Unknown runtime names should pass through (for custom images)."""
        custom_image = "myregistry.com/custom:latest"
        result = resolve_runtime(custom_image)
        assert result == custom_image

    def test_empty_string_passes_through(self):
        """Empty string should pass through (edge case)."""
        result = resolve_runtime("")
        assert result == ""


class TestAvailableRuntimes:
    """Test the function that lists available runtime names."""

    def test_returns_list(self):
        """Should return a list."""
        runtimes = get_available_runtimes()
        assert isinstance(runtimes, list)

    def test_contains_short_names_only(self):
        """Should only contain short names (no colons)."""
        runtimes = get_available_runtimes()
        for runtime in runtimes:
            assert ":" not in runtime, f"Short name should not contain ':' - got {runtime}"

    def test_contains_expected_python_runtimes(self):
        """Should include common Python runtime short names."""
        runtimes = get_available_runtimes()
        assert "python" in runtimes
        assert "python3.11" in runtimes
        assert "python3.12" in runtimes

    def test_contains_expected_node_runtimes(self):
        """Should include common Node runtime short names."""
        runtimes = get_available_runtimes()
        assert "node" in runtimes
        assert "node20" in runtimes

    def test_does_not_contain_full_image_names(self):
        """Should NOT include full image names like 'python:3.11'."""
        runtimes = get_available_runtimes()
        assert "python:3.11" not in runtimes
        assert "node:20" not in runtimes


class TestRuntimeMap:
    """Test the RUNTIME_MAP constant."""

    def test_runtime_map_is_dict(self):
        """RUNTIME_MAP should be a dictionary."""
        assert isinstance(RUNTIME_MAP, dict)

    def test_runtime_map_has_python_entries(self):
        """RUNTIME_MAP should have Python runtime entries."""
        assert "python" in RUNTIME_MAP
        assert "python3.11" in RUNTIME_MAP
        assert "python3.12" in RUNTIME_MAP

    def test_runtime_map_has_node_entries(self):
        """RUNTIME_MAP should have Node runtime entries."""
        assert "node" in RUNTIME_MAP
        assert "node20" in RUNTIME_MAP

    def test_all_short_names_map_to_full_images(self):
        """All short names should map to valid Docker image format."""
        runtimes = get_available_runtimes()
        for short_name in runtimes:
            full_image = RUNTIME_MAP[short_name]
            assert ":" in full_image, f"Full image should have tag: {full_image}"

    def test_default_runtime_is_valid(self):
        """DEFAULT_RUNTIME should be a valid Docker image."""
        assert ":" in DEFAULT_RUNTIME
        assert DEFAULT_RUNTIME == "python:3.11"


class TestRuntimeResolverEdgeCases:
    """Test edge cases and error conditions."""

    def test_whitespace_in_runtime_name(self):
        """Runtime names with whitespace should pass through."""
        result = resolve_runtime("  python  ")
        assert result == "  python  "  # Pass through, let Docker handle validation

    def test_numeric_runtime_name(self):
        """Numeric runtime names should pass through."""
        result = resolve_runtime("12345")
        assert result == "12345"

    def test_special_characters_in_runtime_name(self):
        """Special characters should pass through for custom registries."""
        custom = "my-registry.io/python:3.11-alpine"
        result = resolve_runtime(custom)
        assert result == custom

    @pytest.mark.parametrize("runtime,expected", [
        ("python", "python:3.11"),
        ("python3.12", "python:3.12"),
        ("node", "node:20"),
        ("node18", "node:18"),
        (None, "python:3.11"),
        ("custom:latest", "custom:latest"),
    ])
    def test_parametrized_runtime_resolution(self, runtime, expected):
        """Test multiple runtime resolutions with parametrize."""
        result = resolve_runtime(runtime)
        assert result == expected
