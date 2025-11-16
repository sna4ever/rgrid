"""Structured error classes for RGrid (Tier 3 - Story 10-4).

This module defines all structured error types used throughout the RGrid platform.
Each error type includes:
- Clear, actionable error messages
- Contextual information (file paths, IDs, timestamps, etc.)
- Helpful suggestions for resolving the issue
- JSON serialization for API responses

Error hierarchy:
- RGridError (base class)
  - ValidationError: User input validation errors
  - ExecutionError: Script execution failures
  - TimeoutError: Job timeout errors
  - NetworkError: API/network communication errors
"""

from datetime import datetime
from typing import Optional, Dict, Any, List


class RGridError(Exception):
    """Base error class for all RGrid errors.

    All RGrid errors inherit from this class and include:
    - message: Human-readable error description
    - context: Dictionary of contextual information (file paths, IDs, etc.)
    - timestamp: When the error occurred
    - suggestions: List of actionable steps to resolve the error (optional)

    Errors can be serialized to JSON for API responses using to_dict().
    """

    suggestions: List[str] = []

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize error with message and optional context.

        Args:
            message: Clear, user-friendly error description
            context: Dictionary of contextual information (file paths, IDs, etc.)
        """
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to dictionary for JSON responses.

        Returns:
            Dictionary with error_type, message, context, and timestamp
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class ValidationError(RGridError):
    """User input validation errors.

    Raised when user-provided input is invalid, missing, or malformed.
    Examples:
    - Script file not found
    - Invalid runtime name
    - Missing required parameters
    - Malformed JobSpec
    """

    suggestions = [
        "Check the input parameters are correct",
        "Refer to documentation for valid values",
        "Use --help to see available options"
    ]


class ExecutionError(RGridError):
    """Script execution errors.

    Raised when a script fails during execution.
    Examples:
    - Non-zero exit code
    - Script crashed or threw exception
    - Container failed to start
    - Resource limits exceeded
    """

    suggestions = [
        "Check script logs for details",
        "Verify script runs locally first",
        "Ensure all dependencies are included",
        "Check resource limits (memory, CPU)"
    ]


class TimeoutError(RGridError):
    """Job timeout errors.

    Raised when a job exceeds its configured timeout.
    The timeout exists to prevent runaway jobs from consuming resources.
    """

    suggestions = [
        "Increase timeout with --timeout flag",
        "Optimize script to run faster",
        "Break large jobs into smaller chunks",
        "Check for infinite loops or hangs"
    ]


class NetworkError(RGridError):
    """Network/API communication errors.

    Raised when API calls fail due to network issues.
    Examples:
    - Connection refused
    - API endpoint unreachable
    - HTTP error codes (4xx, 5xx)
    - Timeout connecting to API
    """

    suggestions = [
        "Check network connection",
        "Verify API endpoint is reachable",
        "Check API status page for outages",
        "Retry the request after a brief delay"
    ]


class AuthenticationError(RGridError):
    """Authentication and authorization errors.

    Raised when authentication fails or user lacks permissions.
    Examples:
    - Invalid or expired API token
    - Missing authentication credentials
    - Insufficient permissions for resource
    """

    suggestions = [
        "Check your API token is valid",
        "Run 'rgrid login' to authenticate",
        "Verify you have permission for this resource",
        "Contact support if the issue persists"
    ]


class ResourceNotFoundError(RGridError):
    """Resource not found errors.

    Raised when a requested resource doesn't exist.
    Examples:
    - Job ID not found
    - Execution ID not found
    - Project not found
    """

    suggestions = [
        "Verify the resource ID is correct",
        "Check the resource hasn't been deleted",
        "Use 'rgrid list' to see available resources"
    ]


class QuotaExceededError(RGridError):
    """Quota or rate limit exceeded errors.

    Raised when user exceeds their quota or rate limits.
    Examples:
    - Too many concurrent jobs
    - Storage quota exceeded
    - API rate limit hit
    """

    suggestions = [
        "Wait for existing jobs to complete",
        "Upgrade your plan for higher limits",
        "Delete old artifacts to free up storage",
        "Contact support to discuss quota increases"
    ]
