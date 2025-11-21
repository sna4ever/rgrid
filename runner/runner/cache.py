"""Caching for RGrid (Tier 5 - Stories 6-1, 6-2, and 6-3).

This module provides three levels of caching:

1. Script content caching (Story 6-1):
   - Caches Docker images by script content hash
   - Uses SHA256 hash of raw script content (whitespace-sensitive)
   - Enables instant execution for repeated identical scripts

2. Dependency layer caching (Story 6-2):
   - Caches Docker layers with installed dependencies
   - Uses normalized hash of requirements.txt (order-independent)

3. Combined caching with automatic invalidation (Story 6-3):
   - Caches complete execution environment (script + deps + runtime)
   - Automatically invalidates on ANY change
   - Uses SHA256 hash of combined inputs (order-sensitive)
"""

import hashlib
import logging
from typing import Optional
import psycopg2
import os


logger = logging.getLogger(__name__)


# ============================================================================
# Story 6-1: Script Content Hashing and Cache Lookup
# ============================================================================


def calculate_script_hash(script_content: str) -> str:
    """Calculate SHA256 hash of script content (Story 6-1).

    The hash is computed from the raw script content with NO normalization.
    This is intentional - script whitespace can affect Python behavior
    (indentation), so any change should produce a different hash.

    Args:
        script_content: Python script source code (raw string)

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> calculate_script_hash("print('hello')")
        'abc123...' (64 chars)

        >>> # Whitespace changes produce different hash
        >>> hash1 = calculate_script_hash("print('hi')")
        >>> hash2 = calculate_script_hash("print('hi') ")
        >>> hash1 != hash2
        True

    Note:
        Unlike calculate_deps_hash(), this function does NOT normalize
        whitespace or reorder content. Every character matters.
    """
    # Calculate SHA256 hash of raw script content
    hash_bytes = hashlib.sha256(script_content.encode('utf-8')).digest()
    hash_hex = hash_bytes.hex()

    logger.debug(f"Calculated script_hash: {hash_hex[:16]}... for {len(script_content)} chars")

    return hash_hex


def lookup_script_cache(script_hash: str, runtime: str) -> Optional[str]:
    """Look up cached Docker image by script hash (Story 6-1).

    Args:
        script_hash: SHA256 hash of script content (64 hex chars)
        runtime: Docker runtime image (e.g., "python:3.11")

    Returns:
        Docker image ID if found in cache, None if cache miss

    Examples:
        >>> lookup_script_cache("abc123...", "python:3.11")
        "sha256:image123..."  # Cache hit

        >>> lookup_script_cache("xyz789...", "python:3.11")
        None  # Cache miss

    Note:
        Returns None on database errors (graceful degradation).
        The job will still execute, just without cache benefit.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query the script_cache table
        cursor.execute(
            """
            SELECT docker_image_id FROM script_cache
            WHERE script_hash = %s AND runtime = %s
            """,
            (script_hash, runtime)
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            image_id = result[0]
            logger.info(f"Script cache HIT: {script_hash[:16]}... → {image_id[:20]}...")
            return image_id
        else:
            logger.info(f"Script cache MISS: {script_hash[:16]}...")
            return None

    except Exception as e:
        logger.error(f"Error looking up script cache: {e}")
        # Return None on error (cache miss) - don't fail the job
        return None


def store_script_cache(script_hash: str, runtime: str, docker_image_id: str) -> None:
    """Store new script cache entry (Story 6-1).

    Args:
        script_hash: SHA256 hash of script content (64 hex chars)
        runtime: Docker runtime image (e.g., "python:3.11")
        docker_image_id: Docker image ID (e.g., "sha256:...")

    Raises:
        Exception if database insert fails

    Examples:
        >>> store_script_cache(
        ...     "abc123...",
        ...     "python:3.11",
        ...     "sha256:image123..."
        ... )

    Note:
        Uses upsert (ON CONFLICT DO NOTHING) to handle race conditions
        where multiple workers might cache the same script simultaneously.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into script_cache table with upsert
        cursor.execute(
            """
            INSERT INTO script_cache (script_hash, runtime, docker_image_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (script_hash, runtime) DO NOTHING
            """,
            (script_hash, runtime, docker_image_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Stored script cache: {script_hash[:16]}... → {docker_image_id[:20]}...")

    except Exception as e:
        logger.error(f"Error storing script cache: {e}")
        raise


# ============================================================================
# Story 6-2: Dependency Layer Caching
# ============================================================================


def calculate_deps_hash(requirements_content: str) -> str:
    """Calculate SHA256 hash of requirements.txt content.

    The hash is normalized by:
    - Sorting lines alphabetically (so order doesn't matter)
    - Stripping whitespace from each line
    - Removing empty lines

    This ensures that semantically identical requirements.txt files
    produce the same hash, even if formatted differently.

    Args:
        requirements_content: Raw content of requirements.txt file

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> calculate_deps_hash("numpy==1.24.0\\npandas==2.0.0")
        'abc123...' (64 chars)

        >>> # Same deps, different order = same hash
        >>> hash1 = calculate_deps_hash("pandas==2.0.0\\nnumpy==1.24.0")
        >>> hash2 = calculate_deps_hash("numpy==1.24.0\\npandas==2.0.0")
        >>> hash1 == hash2
        True
    """
    # Normalize: split into lines, strip whitespace, remove empty lines, sort
    lines = [
        line.strip()
        for line in requirements_content.strip().split('\n')
        if line.strip()  # Ignore empty lines
    ]

    # Sort for consistent ordering
    lines_sorted = sorted(lines)

    # Rejoin with newlines
    normalized = '\n'.join(lines_sorted)

    # Calculate SHA256 hash
    hash_bytes = hashlib.sha256(normalized.encode('utf-8')).digest()
    hash_hex = hash_bytes.hex()

    logger.debug(f"Calculated deps_hash: {hash_hex[:16]}... for {len(lines)} dependencies")

    return hash_hex


def get_db_connection():
    """Get database connection for cache operations.

    Returns:
        psycopg2 connection object
    """
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rgrid')

    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def lookup_dependency_cache(deps_hash: str) -> Optional[str]:
    """Look up cached dependency layer by hash.

    Args:
        deps_hash: SHA256 hash of requirements.txt content (64 hex chars)

    Returns:
        Docker layer ID if found in cache, None if cache miss

    Examples:
        >>> lookup_dependency_cache("abc123...")
        "sha256:layer123456..."  # Cache hit

        >>> lookup_dependency_cache("xyz789...")
        None  # Cache miss
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query the dependency_cache table
        cursor.execute(
            "SELECT docker_layer_id FROM dependency_cache WHERE deps_hash = %s",
            (deps_hash,)
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            layer_id = result[0]
            logger.info(f"Cache HIT for deps_hash {deps_hash[:16]}... → layer {layer_id[:20]}...")
            return layer_id
        else:
            logger.info(f"Cache MISS for deps_hash {deps_hash[:16]}...")
            return None

    except Exception as e:
        logger.error(f"Error looking up dependency cache: {e}")
        # Return None on error (cache miss) - don't fail the job
        return None


def store_dependency_cache(deps_hash: str, docker_layer_id: str, requirements_content: str) -> None:
    """Store new dependency cache entry.

    Args:
        deps_hash: SHA256 hash of requirements.txt (64 hex chars)
        docker_layer_id: Docker layer ID (e.g., "sha256:...")
        requirements_content: Original requirements.txt content (for debugging)

    Raises:
        Exception if database insert fails

    Examples:
        >>> store_dependency_cache(
        ...     "abc123...",
        ...     "sha256:layer123...",
        ...     "numpy==1.24.0\\npandas==2.0.0"
        ... )
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into dependency_cache table
        # Use INSERT ... ON CONFLICT DO NOTHING to avoid duplicates
        cursor.execute(
            """
            INSERT INTO dependency_cache (deps_hash, docker_layer_id, requirements_content)
            VALUES (%s, %s, %s)
            ON CONFLICT (deps_hash) DO NOTHING
            """,
            (deps_hash, docker_layer_id, requirements_content)
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Stored cache entry: deps_hash {deps_hash[:16]}... → layer {docker_layer_id[:20]}...")

    except Exception as e:
        logger.error(f"Error storing dependency cache: {e}")
        raise


# ============================================================================
# Story 6-3: Combined Caching with Automatic Invalidation
# ============================================================================


def calculate_combined_hash(
    script_content: str,
    requirements_content: str,
    runtime: str
) -> str:
    """Calculate combined hash for complete cache key (Story 6-3).

    This hash includes ALL inputs that affect execution:
    - Script content (as-is, no normalization)
    - Requirements.txt (as-is, order-sensitive)
    - Runtime (e.g., "python:3.11")

    ANY change to any of these inputs will invalidate the cache.
    This is intentional for data integrity - cache invalidation bugs
    cause data corruption!

    Args:
        script_content: Python script source code
        requirements_content: Raw requirements.txt content
        runtime: Docker runtime image (e.g., "python:3.11")

    Returns:
        64-character hex string (SHA256 hash)

    Examples:
        >>> calculate_combined_hash("print('hi')", "numpy==1.24.0", "python:3.11")
        'abc123...' (64 chars)

        >>> # ANY change invalidates
        >>> hash1 = calculate_combined_hash("print('hi')", "numpy==1.24.0", "python:3.11")
        >>> hash2 = calculate_combined_hash("print('hi')", "numpy==1.25.0", "python:3.11")
        >>> hash1 != hash2  # Different dependency version
        True

    Note:
        Unlike calculate_deps_hash(), this function does NOT normalize
        whitespace or reorder lines. This is intentional - we want to
        invalidate cache on ANY change, even whitespace.
    """
    # Combine all inputs with separators
    # Format: script\n---\nrequirements\n---\nruntime
    combined = f"{script_content}\n---\n{requirements_content}\n---\n{runtime}"

    # Calculate SHA256 hash
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).digest()
    hash_hex = hash_bytes.hex()

    logger.debug(f"Calculated combined_hash: {hash_hex[:16]}... for script + deps + runtime")

    return hash_hex


def lookup_combined_cache(combined_hash: str) -> Optional[str]:
    """Look up cached Docker image by combined hash (Story 6-3).

    Args:
        combined_hash: SHA256 hash of script + deps + runtime (64 hex chars)

    Returns:
        Docker image tag if found in cache, None if cache miss

    Examples:
        >>> lookup_combined_cache("abc123...")
        "rgrid-cached:abc123def456"  # Cache hit

        >>> lookup_combined_cache("xyz789...")
        None  # Cache miss
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query the combined_cache table (or reuse dependency_cache table)
        # For now, we'll create a separate table for combined cache
        cursor.execute(
            "SELECT docker_image_tag FROM combined_cache WHERE combined_hash = %s",
            (combined_hash,)
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            image_tag = result[0]
            logger.info(f"✓ Cache HIT: {combined_hash[:8]}... (using cached image)")
            return image_tag
        else:
            logger.info(f"✗ Cache MISS: {combined_hash[:8]}... (building new image)")
            return None

    except Exception as e:
        logger.error(f"Error looking up combined cache: {e}")
        # Return None on error (cache miss) - don't fail the job
        return None


def store_combined_cache(
    combined_hash: str,
    docker_image_tag: str,
    script_content: str,
    requirements_content: str,
    runtime: str
) -> None:
    """Store new combined cache entry (Story 6-3).

    Args:
        combined_hash: SHA256 hash of script + deps + runtime (64 hex chars)
        docker_image_tag: Docker image tag (e.g., "rgrid-cached:abc123def456")
        script_content: Original script content (for debugging)
        requirements_content: Original requirements.txt content (for debugging)
        runtime: Runtime used (for debugging)

    Raises:
        Exception if database insert fails

    Examples:
        >>> store_combined_cache(
        ...     "abc123...",
        ...     "rgrid-cached:abc123def456",
        ...     "print('test')",
        ...     "numpy==1.24.0",
        ...     "python:3.11"
        ... )

    Note:
        Old cache entries are preserved (not deleted). This allows
        reverting changes to get cache hits on previous versions.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into combined_cache table
        # Use INSERT ... ON CONFLICT DO NOTHING to avoid duplicates
        cursor.execute(
            """
            INSERT INTO combined_cache (
                combined_hash, docker_image_tag, script_content,
                requirements_content, runtime
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (combined_hash) DO NOTHING
            """,
            (combined_hash, docker_image_tag, script_content,
             requirements_content, runtime)
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Stored combined cache: {combined_hash[:8]}... → {docker_image_tag}")

    except Exception as e:
        logger.error(f"Error storing combined cache: {e}")
        raise
