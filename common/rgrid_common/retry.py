"""Auto-retry logic for transient failures (Story 10-7).

This module provides utilities for:
- Classifying errors as transient (retryable) vs permanent
- Determining if an execution should be auto-retried
- Formatting retry status messages

Transient errors are infrastructure failures that may succeed on retry:
- Worker crashes/deaths
- Execution timeouts (may be due to resource contention)
- Out-of-memory kills (may succeed on another worker)
- Network/connection errors

Permanent errors are user/script failures that will fail again:
- Non-zero exit codes from user scripts
- Syntax errors, import errors
- File not found, permission denied
"""

import re
from typing import Optional


# Maximum number of auto-retries (default)
DEFAULT_MAX_RETRIES = 2


# Patterns that indicate transient (retryable) errors
# These are infrastructure failures, not user script failures
TRANSIENT_ERROR_PATTERNS = [
    r"Worker died unexpectedly",
    r"Worker .+ died",
    r"rescheduled",
    r"Execution timeout",
    r"^Killed$",  # OOM killed (exact match)
    r"MemoryError",
    r"ConnectionRefusedError",
    r"Connection timed out",
    r"Connection reset",
    r"Container failed to start",
    r"Docker error",
]


def is_transient_error(error_message: Optional[str], exit_code: int) -> bool:
    """Determine if an error is transient and should be auto-retried.

    Transient errors are infrastructure failures (worker crashes, timeouts,
    OOM) that may succeed on retry. Script failures (non-zero exit codes
    from user code) are NOT transient.

    Args:
        error_message: The error message or execution_error field
        exit_code: The process exit code (-1 for infrastructure errors, >0 for script errors)

    Returns:
        True if the error is transient and should be retried
    """
    # Success is not an error
    if exit_code == 0:
        return False

    # Exit code > 0 typically means user script returned error
    # These are NOT transient - the script will fail again
    if exit_code > 0:
        return False

    # Exit code -1 or similar indicates infrastructure failure
    # Check if error message matches transient patterns
    if not error_message:
        return False

    for pattern in TRANSIENT_ERROR_PATTERNS:
        if re.search(pattern, error_message, re.IGNORECASE):
            return True

    return False


def should_auto_retry(
    error_message: Optional[str],
    exit_code: int,
    retry_count: int,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> bool:
    """Determine if an execution should be automatically retried.

    Args:
        error_message: The error message from the failed execution
        exit_code: The process exit code
        retry_count: Current number of retries already attempted
        max_retries: Maximum number of retries allowed

    Returns:
        True if the execution should be retried
    """
    # Don't retry if we've hit the limit
    if retry_count >= max_retries:
        return False

    # Only retry transient errors
    return is_transient_error(error_message, exit_code)


def format_retry_message(
    retry_count: int,
    max_retries: int,
    reason: str,
) -> str:
    """Format a user-friendly retry status message.

    Args:
        retry_count: Current retry attempt number (1-indexed for display)
        max_retries: Maximum retries allowed
        reason: Reason for the retry (e.g., "worker failure")

    Returns:
        Formatted message like "Auto-retry 1/2 after worker failure"
    """
    return f"Auto-retry {retry_count}/{max_retries} after {reason}"


def format_max_retries_message(
    max_retries: int,
    original_error: Optional[str] = None,
) -> str:
    """Format a message for when max retries have been exceeded.

    Args:
        max_retries: Maximum retries that were attempted
        original_error: The original error message (optional)

    Returns:
        Formatted message explaining max retries exceeded
    """
    base_msg = f"Max retries ({max_retries}) exceeded"
    if original_error:
        # Truncate long errors
        if len(original_error) > 100:
            original_error = original_error[:100] + "..."
        return f"{base_msg}. Original error: {original_error}"
    return base_msg


def get_retry_reason(error_message: Optional[str]) -> str:
    """Extract a short reason for the retry from the error message.

    Args:
        error_message: The full error message

    Returns:
        Short description like "worker failure", "timeout", etc.
    """
    if not error_message:
        return "unknown error"

    error_lower = error_message.lower()

    if "worker" in error_lower and ("died" in error_lower or "crash" in error_lower):
        return "worker failure"
    if "timeout" in error_lower:
        return "timeout"
    if "killed" in error_lower or "memory" in error_lower:
        return "out of memory"
    if "connection" in error_lower:
        return "connection error"
    if "docker" in error_lower or "container" in error_lower:
        return "container error"

    return "transient failure"
