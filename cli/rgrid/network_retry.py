"""Network retry logic with exponential backoff (Story 10-5).

Provides graceful handling of transient network failures with automatic
retry and user-friendly progress messages.
"""

import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type, TypeVar, ParamSpec
import httpx
from rich.console import Console

from rgrid_common.errors import NetworkError

# Console for displaying retry messages
console = Console(stderr=True)

P = ParamSpec('P')
T = TypeVar('T')


# Exceptions that should trigger automatic retry
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)

# HTTP status codes that should trigger automatic retry
RETRYABLE_STATUS_CODES = {502, 503, 504}


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    # Check for network/transport errors
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    # Check for retryable HTTP status codes
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES

    return False


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 5
    """Maximum number of retry attempts after initial failure."""

    initial_delay: float = 1.0
    """Initial delay in seconds before first retry."""

    max_delay: float = 30.0
    """Maximum delay in seconds between retries."""

    backoff_factor: float = 2.0
    """Factor by which to multiply delay for each subsequent retry."""

    on_retry: Optional[Callable[[int, int, Exception], None]] = field(default=None)
    """Optional callback called on each retry with (attempt, max_attempts, error)."""

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff.

        Args:
            attempt: Zero-based attempt number (0 for first retry)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


def with_retry(
    func: Callable[[], Any],
    config: Optional[RetryConfig] = None,
) -> Any:
    """
    Execute a function with automatic retry on transient failures.

    Args:
        func: Zero-argument callable to execute
        config: Retry configuration (uses defaults if not provided)

    Returns:
        Result from successful function call

    Raises:
        Exception: The last exception if all retries are exhausted,
                   or immediately for non-retryable errors
    """
    if config is None:
        config = RetryConfig()

    last_error: Optional[Exception] = None
    # Total attempts = initial + max_retries
    total_attempts = 1 + config.max_retries

    for attempt in range(total_attempts):
        try:
            return func()
        except Exception as e:
            last_error = e

            # Check if this error is retryable
            if not is_retryable_error(e):
                raise

            # Check if we have more retries left
            if attempt + 1 >= total_attempts:
                # No more retries, raise the error
                raise

            # Calculate delay for this retry
            delay = config.get_delay(attempt)

            # Call the retry callback if provided
            if config.on_retry:
                # attempt + 2 because: attempt is 0-based, and we're about to do next attempt
                config.on_retry(attempt + 2, config.max_retries, e)

            # Wait before retrying
            time.sleep(delay)

    # Should never reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in retry loop")


def default_retry_callback(attempt: int, max_attempts: int, error: Exception) -> None:
    """
    Default callback for displaying retry progress messages.

    Displays messages in the format: "Connection lost. Retrying... (attempt 2/5)"

    Args:
        attempt: Current attempt number (1-based, starting from 2 for first retry)
        max_attempts: Maximum number of retry attempts
        error: The exception that triggered the retry
    """
    console.print(
        f"[yellow]Connection lost. Retrying... (attempt {attempt}/{max_attempts})[/yellow]"
    )


def create_api_wrapper(
    func: Callable[P, T],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Callable[P, T]:
    """
    Create a wrapper that adds retry logic to an API function.

    This factory function wraps any callable with automatic retry logic
    for transient network failures. On persistent failure, it raises
    a NetworkError with a user-friendly message.

    Args:
        func: The function to wrap
        max_retries: Maximum number of retry attempts (default: 5)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay between retries (default: 30.0)

    Returns:
        Wrapped function with retry logic

    Example:
        >>> wrapped_get = create_api_wrapper(client.get_execution)
        >>> result = wrapped_get(execution_id)  # Will retry on network errors
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        on_retry=default_retry_callback,
    )

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return with_retry(lambda: func(*args, **kwargs), config)
        except RETRYABLE_EXCEPTIONS as e:
            # Convert to user-friendly NetworkError on persistent failure
            raise NetworkError(
                "Network error. Check connection and retry.",
                context={"original_error": str(e)},
            ) from e
        except httpx.HTTPStatusError as e:
            # Also convert retryable HTTP errors to NetworkError
            if e.response.status_code in RETRYABLE_STATUS_CODES:
                raise NetworkError(
                    "Network error. Check connection and retry.",
                    context={
                        "status_code": e.response.status_code,
                        "original_error": str(e),
                    },
                ) from e
            # Non-retryable HTTP errors pass through
            raise

    return wrapper
