"""Unit tests for execution metadata tagging (Story 10-8)."""

import pytest
from unittest.mock import Mock, patch


class TestMetadataParsing:
    """Test parsing of --metadata key=value flags in CLI."""

    def test_parse_single_metadata(self):
        """Parse a single metadata key=value pair."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata(["project=ml-model"])
        assert result == {"project": "ml-model"}

    def test_parse_multiple_metadata(self):
        """Parse multiple metadata key=value pairs."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata(["project=ml-model", "env=prod", "team=data-science"])
        assert result == {
            "project": "ml-model",
            "env": "prod",
            "team": "data-science"
        }

    def test_parse_empty_metadata(self):
        """Parse empty metadata list returns empty dict."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata([])
        assert result == {}

    def test_parse_metadata_with_equals_in_value(self):
        """Parse metadata where value contains equals sign."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata(["url=http://example.com?param=value"])
        assert result == {"url": "http://example.com?param=value"}

    def test_parse_metadata_with_spaces_in_value(self):
        """Parse metadata where value contains spaces."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata(["description=My ML Model"])
        assert result == {"description": "My ML Model"}

    def test_parse_invalid_metadata_missing_equals(self):
        """Raise error for metadata without equals sign."""
        from rgrid.utils.metadata_parser import parse_metadata, MetadataParseError

        with pytest.raises(MetadataParseError, match="Invalid metadata format"):
            parse_metadata(["invalid"])

    def test_parse_invalid_metadata_empty_key(self):
        """Raise error for metadata with empty key."""
        from rgrid.utils.metadata_parser import parse_metadata, MetadataParseError

        with pytest.raises(MetadataParseError, match="Invalid metadata format"):
            parse_metadata(["=value"])

    def test_parse_metadata_duplicate_keys_last_wins(self):
        """When duplicate keys, last value wins."""
        from rgrid.utils.metadata_parser import parse_metadata

        result = parse_metadata(["env=dev", "env=prod"])
        assert result == {"env": "prod"}


class TestMetadataFiltering:
    """Test metadata filtering logic in API queries."""

    def test_build_filter_single_metadata(self):
        """Build SQL filter for single metadata key=value."""
        from rgrid.utils.metadata_parser import build_metadata_filter

        # JSONB filtering in Postgres: metadata @> '{"key": "value"}'::jsonb
        filter_dict = build_metadata_filter({"project": "ml-model"})
        assert filter_dict == {"project": "ml-model"}

    def test_build_filter_multiple_metadata(self):
        """Build SQL filter for multiple metadata key=value pairs."""
        from rgrid.utils.metadata_parser import build_metadata_filter

        filter_dict = build_metadata_filter({"project": "ml-model", "env": "prod"})
        assert filter_dict == {"project": "ml-model", "env": "prod"}

    def test_build_filter_empty_metadata(self):
        """Build filter for empty metadata returns None."""
        from rgrid.utils.metadata_parser import build_metadata_filter

        result = build_metadata_filter({})
        assert result is None or result == {}


class TestMetadataValidation:
    """Test metadata validation rules."""

    def test_metadata_keys_are_strings(self):
        """All metadata keys must be strings."""
        from rgrid.utils.metadata_parser import validate_metadata

        # Valid
        assert validate_metadata({"key": "value"}) is True

        # Invalid - numeric key (this would only happen if programmatically created)
        # In CLI parsing, all keys are strings by default

    def test_metadata_values_are_strings(self):
        """All metadata values must be strings."""
        from rgrid.utils.metadata_parser import validate_metadata

        # Valid
        assert validate_metadata({"key": "value"}) is True

        # Note: CLI always produces string values, so this is more for API validation

    def test_metadata_max_size(self):
        """Metadata should not exceed reasonable size limits."""
        from rgrid.utils.metadata_parser import validate_metadata, MetadataValidationError

        # Valid - reasonable size
        metadata = {f"key{i}": f"value{i}" for i in range(10)}
        assert validate_metadata(metadata) is True

        # Invalid - too many keys (limit: 50)
        large_metadata = {f"key{i}": f"value{i}" for i in range(51)}
        with pytest.raises(MetadataValidationError, match="Too many metadata keys"):
            validate_metadata(large_metadata)

    def test_metadata_key_length(self):
        """Metadata keys should have reasonable length limits."""
        from rgrid.utils.metadata_parser import validate_metadata, MetadataValidationError

        # Valid - reasonable key length
        assert validate_metadata({"short_key": "value"}) is True

        # Invalid - key too long (limit: 100 chars)
        long_key = "k" * 101
        with pytest.raises(MetadataValidationError, match="Key too long"):
            validate_metadata({long_key: "value"})

    def test_metadata_value_length(self):
        """Metadata values should have reasonable length limits."""
        from rgrid.utils.metadata_parser import validate_metadata, MetadataValidationError

        # Valid - reasonable value length
        assert validate_metadata({"key": "short_value"}) is True

        # Invalid - value too long (limit: 1000 chars)
        long_value = "v" * 1001
        with pytest.raises(MetadataValidationError, match="Value too long"):
            validate_metadata({"key": long_value})
