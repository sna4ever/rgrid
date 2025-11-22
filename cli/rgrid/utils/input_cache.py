"""Input file caching utilities (Story 6-4).

This module provides functions for calculating input file hashes
to enable caching of identical input files across executions.

The caching strategy:
1. Calculate SHA256 hash of all input file contents (combined)
2. Check API for cache hit (hash matches existing entry)
3. If hit: skip upload, reuse cached MinIO references
4. If miss: upload files, store cache entry for future reuse
"""

import hashlib
from pathlib import Path
from typing import List


def calculate_input_hash(file_contents: List[bytes]) -> str:
    """Calculate combined SHA256 hash of multiple input file contents.

    The hash is calculated by:
    1. Computing SHA256 hash of each file's content
    2. Sorting the individual hashes (for order independence)
    3. Combining sorted hashes into a final SHA256 hash

    This ensures the same set of files produces the same hash
    regardless of the order they are provided.

    Args:
        file_contents: List of file contents (bytes)

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> calculate_input_hash([b"Hello", b"World"])
        'abc123...' (64 chars)

        >>> # Same files in different order = same hash
        >>> hash1 = calculate_input_hash([b"A", b"B"])
        >>> hash2 = calculate_input_hash([b"B", b"A"])
        >>> hash1 == hash2
        True
    """
    # Calculate individual file hashes
    file_hashes = []
    for content in file_contents:
        file_hash = hashlib.sha256(content).hexdigest()
        file_hashes.append(file_hash)

    # Sort for order independence
    file_hashes.sort()

    # Combine sorted hashes into final hash
    combined = "|".join(file_hashes)
    final_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()

    return final_hash


def calculate_input_hash_from_files(file_paths: List[str]) -> str:
    """Calculate combined SHA256 hash from file paths.

    Reads all files and computes the combined hash. This is the
    main entry point for CLI usage.

    Args:
        file_paths: List of file paths to hash

    Returns:
        64-character hex string (SHA256 hash)

    Raises:
        FileNotFoundError: If any file does not exist

    Examples:
        >>> calculate_input_hash_from_files(["input1.csv", "input2.csv"])
        'def456...' (64 chars)
    """
    file_contents = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        content = path.read_bytes()
        file_contents.append(content)

    return calculate_input_hash(file_contents)
