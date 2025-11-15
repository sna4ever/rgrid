"""
Pre-configured runtime mappings.

Maps short runtime names to Docker images for better UX.
"""

from typing import Dict

# Runtime name -> Docker image mapping
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

    # Full image names (pass through)
    "python:3.11": "python:3.11",
    "python:3.12": "python:3.12",
    "python:3.10": "python:3.10",
    "python:3.9": "python:3.9",
    "node:20": "node:20",
    "node:18": "node:18",
}

DEFAULT_RUNTIME = "python:3.11"


def resolve_runtime(runtime: str | None) -> str:
    """
    Resolve runtime name to Docker image.

    Args:
        runtime: Runtime name (short or full), or None for default

    Returns:
        Docker image name

    Examples:
        >>> resolve_runtime(None)
        'python:3.11'
        >>> resolve_runtime("python")
        'python:3.11'
        >>> resolve_runtime("python3.12")
        'python:3.12'
        >>> resolve_runtime("node")
        'node:20'
    """
    if runtime is None:
        return DEFAULT_RUNTIME

    # Try to resolve from map
    return RUNTIME_MAP.get(runtime, runtime)


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
