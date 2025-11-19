"""Utility functions for parsing and validating execution metadata (Story 10-8)."""

from typing import Dict, List, Optional


class MetadataParseError(Exception):
    """Raised when metadata parsing fails."""
    pass


class MetadataValidationError(Exception):
    """Raised when metadata validation fails."""
    pass


# Validation limits
MAX_METADATA_KEYS = 50
MAX_KEY_LENGTH = 100
MAX_VALUE_LENGTH = 1000


def parse_metadata(metadata_list: List[str]) -> Dict[str, str]:
    """
    Parse metadata from list of "key=value" strings.

    Args:
        metadata_list: List of "key=value" strings

    Returns:
        Dictionary of metadata key-value pairs

    Raises:
        MetadataParseError: If parsing fails

    Examples:
        >>> parse_metadata(["project=ml-model", "env=prod"])
        {"project": "ml-model", "env": "prod"}

        >>> parse_metadata(["url=http://example.com?param=value"])
        {"url": "http://example.com?param=value"}
    """
    metadata = {}

    for item in metadata_list:
        if "=" not in item:
            raise MetadataParseError(
                f"Invalid metadata format: '{item}'. Expected 'key=value'"
            )

        # Split on first '=' to handle values with '=' in them
        key, value = item.split("=", 1)

        # Validate key is not empty
        if not key.strip():
            raise MetadataParseError(
                f"Invalid metadata format: '{item}'. Key cannot be empty"
            )

        metadata[key] = value

    return metadata


def build_metadata_filter(metadata: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Build metadata filter for database queries.

    This uses PostgreSQL's JSONB containment operator (@>).
    The filter dict will be used with SQLAlchemy's contains() method.

    Args:
        metadata: Metadata dictionary to filter by

    Returns:
        Filter dictionary for JSONB @> query, or None if empty

    Examples:
        >>> build_metadata_filter({"project": "ml-model"})
        {"project": "ml-model"}

        >>> build_metadata_filter({})
        None
    """
    if not metadata:
        return None

    return metadata


def validate_metadata(metadata: Dict[str, str]) -> bool:
    """
    Validate metadata against size and format limits.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        True if valid

    Raises:
        MetadataValidationError: If validation fails

    Examples:
        >>> validate_metadata({"key": "value"})
        True

        >>> validate_metadata({f"key{i}": f"value{i}" for i in range(51)})
        MetadataValidationError: Too many metadata keys
    """
    # Check number of keys
    if len(metadata) > MAX_METADATA_KEYS:
        raise MetadataValidationError(
            f"Too many metadata keys: {len(metadata)} (max: {MAX_METADATA_KEYS})"
        )

    # Check key and value lengths
    for key, value in metadata.items():
        if len(key) > MAX_KEY_LENGTH:
            raise MetadataValidationError(
                f"Key too long: '{key}' ({len(key)} chars, max: {MAX_KEY_LENGTH})"
            )

        if len(value) > MAX_VALUE_LENGTH:
            raise MetadataValidationError(
                f"Value too long for key '{key}' ({len(value)} chars, max: {MAX_VALUE_LENGTH})"
            )

    return True
