"""Network retry logic with exponential backoff (Story 10-5).

This module provides retry functionality for handling transient network failures.
It implements exponential backoff with user-friendly status messages.
"""

import time
from functools import wraps
from typing import Callable, Any
import httpx
import click


def calculate_backoff_delay(attempt: int) -> int:
    """Calculate exponential backoff delay for a retry attempt.

    Args:
        attempt: Retry attempt number (1-based)

    Returns:
        Delay in seconds (2, 4, 8, 16, 16...)
    """
    # Exponential backoff: 2^attempt, capped at 16 seconds
    delay = 2 ** attempt
    return min(delay, 16)


def should_retry_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry.

    Retries on:
    - Connection errors (httpx.ConnectError)
    - Timeout errors (httpx.TimeoutException)
    - Network errors (httpx.NetworkError)
    - 5xx server errors (500, 502, 503, 504, etc.)

    Does NOT retry on:
    - 4xx client errors (400, 401, 404, etc.)
    - Other unknown errors

    Args:
        error: Exception that was raised

    Returns:
        True if should retry, False otherwise
    """
    # Connection errors
    if isinstance(error, httpx.ConnectError):
        return True

    # Timeout errors
    if isinstance(error, httpx.TimeoutException):
        return True

    # Network errors
    if isinstance(error, httpx.NetworkError):
        return True

    # HTTP status errors
    if isinstance(error, httpx.HTTPStatusError):
        # Retry on 5xx server errors
        if 500 <= error.response.status_code < 600:
            return True
        # Don't retry on 4xx client errors
        return False

    # Don't retry unknown errors
    return False


def retry_with_backoff(max_retries: int = 5) -> Callable:
    """Decorator that retries a function with exponential backoff.

    Automatically retries network operations on transient failures:
    - Displays "Connection lost. Retrying... (attempt X/5)"
    - Uses exponential backoff: 2s, 4s, 8s, 16s
    - On success, continues seamlessly
    - On persistent failure, displays helpful error message

    Args:
        max_retries: Maximum number of retry attempts (default: 5)

    Returns:
        Decorator function

    Example:
        @retry_with_backoff(max_retries=5)
        def make_api_call():
            response = client.get("/api/endpoint")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    # Try to execute the function
                    return func(*args, **kwargs)

                except Exception as error:
                    last_error = error

                    # Check if we should retry this error
                    if not should_retry_error(error):
                        # Don't retry - raise immediately
                        raise

                    # Check if we've exhausted retries
                    if attempt >= max_retries:
                        # Final failure - display helpful message
                        click.echo(
                            "\n❌ Network error. Check connection and retry.\n",
                            err=True
                        )
                        raise

                    # Display retry message
                    # Show next attempt number (e.g., after attempt 0 fails, show "attempt 2")
                    next_attempt = attempt + 2
                    click.echo(
                        f"⚠️  Connection lost. Retrying... (attempt {next_attempt}/{max_retries})",
                        err=True
                    )

                    # Calculate and wait for backoff delay
                    delay = calculate_backoff_delay(attempt + 1)
                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_error:
                raise last_error

        return wrapper
    return decorator
