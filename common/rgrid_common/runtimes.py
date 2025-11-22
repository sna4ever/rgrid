"""
Pre-configured runtime mappings.

Maps short runtime names to Docker images for better UX.

SECURITY: Only explicitly allowlisted runtimes are permitted.
Arbitrary Docker images are NOT allowed to prevent:
- Dockerfile injection attacks during image builds
- Execution of malicious Docker images
- Supply chain attacks via untrusted images
"""

import re
from typing import Dict


class UnsupportedRuntimeError(ValueError):
    """Raised when an unsupported runtime is requested."""
    pass


# Runtime name -> Docker image mapping (ALLOWLIST)
# SECURITY: This is the ONLY source of valid runtimes
RUNTIME_MAP: Dict[str, str] = {
    # Python runtimes
    "python": "python:3.11",
    "python3.11": "python:3.11",
    "python3.12": "python:3.12",
    "python3.10": "python:3.10",
    "python3.9": "python:3.9",

    # Node.js runtimes
    "node": "node:20",
    "node20": "node:20",
    "node18": "node:18",

    # Full image names (pass through - still must be in allowlist)
    "python:3.11": "python:3.11",
    "python:3.12": "python:3.12",
    "python:3.10": "python:3.10",
    "python:3.9": "python:3.9",
    "node:20": "node:20",
    "node:18": "node:18",
}

DEFAULT_RUNTIME = "python:3.11"

# SECURITY: Pattern to validate Docker image names (used for additional validation)
# Valid format: name:tag where name is alphanumeric/dots/dashes and tag is alphanumeric/dots/dashes
DOCKER_IMAGE_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*:[a-zA-Z0-9][a-zA-Z0-9._-]*$')


def resolve_runtime(runtime: str | None) -> str:
    """
    Resolve runtime name to Docker image.

    SECURITY: Only returns images from the RUNTIME_MAP allowlist.
    Unknown runtimes raise UnsupportedRuntimeError to prevent arbitrary
    image execution.

    Args:
        runtime: Runtime name (short or full), or None for default

    Returns:
        Docker image name from allowlist

    Raises:
        UnsupportedRuntimeError: If runtime is not in the allowlist

    Examples:
        >>> resolve_runtime(None)
        'python:3.11'
        >>> resolve_runtime("python")
        'python:3.11'
        >>> resolve_runtime("python3.12")
        'python:3.12'
        >>> resolve_runtime("node")
        'node:20'
        >>> resolve_runtime("malicious:image")
        Raises UnsupportedRuntimeError
    """
    if runtime is None:
        return DEFAULT_RUNTIME

    # SECURITY: Only allow explicitly listed runtimes
    resolved = RUNTIME_MAP.get(runtime)
    if resolved is None:
        available = get_available_runtimes()
        raise UnsupportedRuntimeError(
            f"Unsupported runtime: '{runtime}'. "
            f"Available runtimes: {', '.join(sorted(available))}"
        )

    # Additional validation: ensure resolved image matches expected pattern
    if not DOCKER_IMAGE_PATTERN.match(resolved):
        raise UnsupportedRuntimeError(
            f"Invalid Docker image format in allowlist: '{resolved}'"
        )

    return resolved


def get_available_runtimes() -> list[str]:
    """
    Get list of available short runtime names.

    Returns:
        List of runtime names
    """
    # Return only the short names (exclude full image names)
    return [
        name for name in RUNTIME_MAP.keys()
        if ":" not in name
    ]
