"""
Unit tests for network retry logic (Story 10-5).

Tests the retry decorator with exponential backoff for network failures.
"""

import pytest
from unittest.mock import Mock, patch, call
import httpx
import time
from rgrid.retry import (
    retry_with_backoff,
    should_retry_error,
    calculate_backoff_delay,
)


class TestRetryBackoffCalculation:
    """Test backoff delay calculation."""

    def test_backoff_delay_attempt_1(self):
        """First retry should wait 2 seconds."""
        assert calculate_backoff_delay(1) == 2

    def test_backoff_delay_attempt_2(self):
        """Second retry should wait 4 seconds."""
        assert calculate_backoff_delay(2) == 4

    def test_backoff_delay_attempt_3(self):
        """Third retry should wait 8 seconds."""
        assert calculate_backoff_delay(3) == 8

    def test_backoff_delay_attempt_4(self):
        """Fourth retry should wait 16 seconds."""
        assert calculate_backoff_delay(4) == 16

    def test_backoff_delay_max_attempts(self):
        """Fifth retry should wait 16 seconds (max)."""
        assert calculate_backoff_delay(5) == 16


class TestShouldRetryError:
    """Test which errors should trigger retry."""

    def test_connection_error_should_retry(self):
        """Connection errors should trigger retry."""
        error = httpx.ConnectError("Connection failed")
        assert should_retry_error(error) is True

    def test_timeout_error_should_retry(self):
        """Timeout errors should trigger retry."""
        error = httpx.TimeoutException("Request timed out")
        assert should_retry_error(error) is True

    def test_network_error_should_retry(self):
        """Network errors should trigger retry."""
        error = httpx.NetworkError("Network unreachable")
        assert should_retry_error(error) is True

    def test_5xx_error_should_retry(self):
        """500 Internal Server Error should trigger retry."""
        response = Mock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=Mock(), response=response)
        assert should_retry_error(error) is True

    def test_503_error_should_retry(self):
        """503 Service Unavailable should trigger retry."""
        response = Mock()
        response.status_code = 503
        error = httpx.HTTPStatusError("Service unavailable", request=Mock(), response=response)
        assert should_retry_error(error) is True

    def test_400_error_should_not_retry(self):
        """400 Bad Request should NOT trigger retry."""
        response = Mock()
        response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)
        assert should_retry_error(error) is False

    def test_401_error_should_not_retry(self):
        """401 Unauthorized should NOT trigger retry."""
        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=response)
        assert should_retry_error(error) is False

    def test_404_error_should_not_retry(self):
        """404 Not Found should NOT trigger retry."""
        response = Mock()
        response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=Mock(), response=response)
        assert should_retry_error(error) is False

    def test_unknown_error_should_not_retry(self):
        """Unknown errors should NOT trigger retry."""
        error = ValueError("Some other error")
        assert should_retry_error(error) is False


class TestRetryDecorator:
    """Test the retry decorator functionality."""

    def test_successful_call_no_retry(self):
        """Successful call should not retry."""
        mock_func = Mock(return_value="success")
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_on_connection_error(self, mock_echo, mock_sleep):
        """Should retry on connection error and succeed."""
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            "success"
        ])
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3
        # Should have slept twice (2s, 4s)
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list == [call(2), call(4)]
        # Should display retry messages
        assert mock_echo.call_count >= 2

    @patch('time.sleep')
    @patch('click.echo')
    def test_max_retries_exceeded(self, mock_echo, mock_sleep):
        """Should fail after max retries exceeded."""
        # Always fail
        mock_func = Mock(side_effect=httpx.ConnectError("Connection failed"))
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        with pytest.raises(httpx.ConnectError):
            decorated()

        # Should try 6 times (initial + 5 retries)
        assert mock_func.call_count == 6
        # Should sleep 5 times
        assert mock_sleep.call_count == 5
        # Backoff delays: 2s, 4s, 8s, 16s, 16s
        assert mock_sleep.call_args_list == [
            call(2), call(4), call(8), call(16), call(16)
        ]

    @patch('time.sleep')
    @patch('click.echo')
    def test_no_retry_on_4xx_error(self, mock_echo, mock_sleep):
        """Should NOT retry on 4xx client errors."""
        response = Mock()
        response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=Mock(), response=response)
        mock_func = Mock(side_effect=error)
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        with pytest.raises(httpx.HTTPStatusError):
            decorated()

        # Should try only once (no retries)
        assert mock_func.call_count == 1
        # Should not sleep
        assert mock_sleep.call_count == 0

    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_on_timeout(self, mock_echo, mock_sleep):
        """Should retry on timeout error."""
        # Timeout once, then succeed
        mock_func = Mock(side_effect=[
            httpx.TimeoutException("Request timed out"),
            "success"
        ])
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args_list == [call(2)]

    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_message_displays_attempt_count(self, mock_echo, mock_sleep):
        """Retry messages should display attempt count."""
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            "success"
        ])
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated()

        # Check that retry messages were displayed
        calls = [str(call) for call in mock_echo.call_args_list]
        # Should contain retry messages with attempt numbers
        assert any("attempt 2/5" in str(call).lower() for call in calls)
        assert any("attempt 3/5" in str(call).lower() for call in calls)

    @patch('time.sleep')
    @patch('click.echo')
    def test_final_failure_message(self, mock_echo, mock_sleep):
        """Should display helpful message on persistent failure."""
        mock_func = Mock(side_effect=httpx.ConnectError("Connection failed"))
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        with pytest.raises(httpx.ConnectError):
            decorated()

        # Check that final error message was displayed
        calls = [str(call) for call in mock_echo.call_args_list]
        # Should contain final error message
        assert any("network error" in str(call).lower() for call in calls)

    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_preserves_function_return_value(self, mock_echo, mock_sleep):
        """Retry should preserve original function return value."""
        expected_result = {"key": "value", "number": 42}
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection failed"),
            expected_result
        ])
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated()

        assert result == expected_result

    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_preserves_function_args(self, mock_echo, mock_sleep):
        """Retry should call function with same args each time."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection failed"),
            "success"
        ])
        decorated = retry_with_backoff(max_retries=5)(mock_func)

        result = decorated("arg1", "arg2", kwarg1="value1")

        # Both calls should have same arguments
        assert mock_func.call_count == 2
        assert all(
            call == (("arg1", "arg2"), {"kwarg1": "value1"})
            for call in [c for c in mock_func.call_args_list]
        )
