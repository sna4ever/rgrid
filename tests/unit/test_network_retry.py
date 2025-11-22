"""Unit tests for network failure graceful handling (Story 10-5).

Tests the retry mechanism with exponential backoff for transient network errors.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from rgrid.network_retry import (
    with_retry,
    RetryConfig,
    is_retryable_error,
    RETRYABLE_EXCEPTIONS,
    default_retry_callback,
    create_api_wrapper,
)


class TestIsRetryableError:
    """Test identification of retryable errors."""

    def test_connect_error_is_retryable(self):
        """ConnectError (connection refused, DNS failure) should be retryable."""
        error = httpx.ConnectError("Connection refused")
        assert is_retryable_error(error) is True

    def test_connect_timeout_is_retryable(self):
        """ConnectTimeout should be retryable."""
        error = httpx.ConnectTimeout("Connection timed out")
        assert is_retryable_error(error) is True

    def test_read_timeout_is_retryable(self):
        """ReadTimeout should be retryable."""
        error = httpx.ReadTimeout("Read timed out")
        assert is_retryable_error(error) is True

    def test_write_timeout_is_retryable(self):
        """WriteTimeout should be retryable."""
        error = httpx.WriteTimeout("Write timed out")
        assert is_retryable_error(error) is True

    def test_pool_timeout_is_retryable(self):
        """PoolTimeout should be retryable."""
        error = httpx.PoolTimeout("Pool timed out")
        assert is_retryable_error(error) is True

    def test_http_status_error_not_retryable_by_default(self):
        """HTTPStatusError (4xx/5xx) should not be retryable by default."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(400, request=request)
        error = httpx.HTTPStatusError("Bad request", request=request, response=response)
        assert is_retryable_error(error) is False

    def test_503_service_unavailable_is_retryable(self):
        """503 Service Unavailable should be retryable."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(503, request=request)
        error = httpx.HTTPStatusError("Service unavailable", request=request, response=response)
        assert is_retryable_error(error) is True

    def test_502_bad_gateway_is_retryable(self):
        """502 Bad Gateway should be retryable."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(502, request=request)
        error = httpx.HTTPStatusError("Bad gateway", request=request, response=response)
        assert is_retryable_error(error) is True

    def test_504_gateway_timeout_is_retryable(self):
        """504 Gateway Timeout should be retryable."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(504, request=request)
        error = httpx.HTTPStatusError("Gateway timeout", request=request, response=response)
        assert is_retryable_error(error) is True

    def test_generic_exception_not_retryable(self):
        """Generic exceptions should not be retryable."""
        error = ValueError("Something went wrong")
        assert is_retryable_error(error) is False


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Default config should have 5 retries and exponential backoff."""
        config = RetryConfig()
        assert config.max_retries == 5
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0

    def test_custom_config(self):
        """Custom config should override defaults."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.5,
            max_delay=10.0,
            backoff_factor=1.5,
        )
        assert config.max_retries == 3
        assert config.initial_delay == 0.5
        assert config.max_delay == 10.0
        assert config.backoff_factor == 1.5

    def test_get_delay_exponential_backoff(self):
        """Delay should increase exponentially with attempt number."""
        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_delay=30.0)

        assert config.get_delay(0) == 1.0   # 1 * 2^0 = 1
        assert config.get_delay(1) == 2.0   # 1 * 2^1 = 2
        assert config.get_delay(2) == 4.0   # 1 * 2^2 = 4
        assert config.get_delay(3) == 8.0   # 1 * 2^3 = 8
        assert config.get_delay(4) == 16.0  # 1 * 2^4 = 16

    def test_get_delay_respects_max(self):
        """Delay should not exceed max_delay."""
        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_delay=5.0)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 5.0  # Capped at max_delay
        assert config.get_delay(4) == 5.0  # Capped at max_delay


class TestWithRetry:
    """Test the with_retry decorator/function."""

    def test_success_on_first_attempt(self):
        """Function should return immediately on success."""
        mock_func = Mock(return_value={"status": "ok"})

        result = with_retry(mock_func, RetryConfig(max_retries=5))

        assert result == {"status": "ok"}
        assert mock_func.call_count == 1

    def test_success_after_retries(self):
        """Function should succeed after transient failures."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            {"status": "ok"},
        ])

        with patch('time.sleep'):  # Don't actually sleep in tests
            result = with_retry(mock_func, RetryConfig(max_retries=5))

        assert result == {"status": "ok"}
        assert mock_func.call_count == 3

    def test_exhausts_retries_and_raises(self):
        """Function should raise after exhausting all retries."""
        mock_func = Mock(side_effect=httpx.ConnectError("Connection refused"))

        with patch('time.sleep'):
            with pytest.raises(httpx.ConnectError):
                with_retry(mock_func, RetryConfig(max_retries=3))

        # Initial attempt + 3 retries = 4 calls
        assert mock_func.call_count == 4

    def test_non_retryable_error_raises_immediately(self):
        """Non-retryable errors should not trigger retry."""
        mock_func = Mock(side_effect=ValueError("Invalid data"))

        with pytest.raises(ValueError):
            with_retry(mock_func, RetryConfig(max_retries=5))

        assert mock_func.call_count == 1

    def test_http_400_not_retried(self):
        """HTTP 400 errors should not be retried."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(400, request=request)
        error = httpx.HTTPStatusError("Bad request", request=request, response=response)
        mock_func = Mock(side_effect=error)

        with pytest.raises(httpx.HTTPStatusError):
            with_retry(mock_func, RetryConfig(max_retries=5))

        assert mock_func.call_count == 1

    def test_http_503_is_retried(self):
        """HTTP 503 errors should be retried."""
        request = httpx.Request("GET", "http://test.com")
        response = httpx.Response(503, request=request)
        error = httpx.HTTPStatusError("Service unavailable", request=request, response=response)
        mock_func = Mock(side_effect=[error, error, {"status": "ok"}])

        with patch('time.sleep'):
            result = with_retry(mock_func, RetryConfig(max_retries=5))

        assert result == {"status": "ok"}
        assert mock_func.call_count == 3

    @patch('time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        """Retry should use exponential backoff delays."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            {"status": "ok"},
        ])

        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_retries=5)
        result = with_retry(mock_func, config)

        assert result == {"status": "ok"}
        # Check sleep was called with exponential delays
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1.0)  # First retry
        mock_sleep.assert_any_call(2.0)  # Second retry
        mock_sleep.assert_any_call(4.0)  # Third retry


class TestRetryMessages:
    """Test retry progress messages."""

    @patch('time.sleep')
    def test_displays_retry_message(self, mock_sleep):
        """Should display 'Connection lost. Retrying...' message."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection refused"),
            {"status": "ok"},
        ])
        messages = []

        def on_retry(attempt, max_attempts, error):
            messages.append(f"Connection lost. Retrying... (attempt {attempt}/{max_attempts})")

        config = RetryConfig(max_retries=5, on_retry=on_retry)
        result = with_retry(mock_func, config)

        assert result == {"status": "ok"}
        assert len(messages) == 1
        assert messages[0] == "Connection lost. Retrying... (attempt 2/5)"

    @patch('time.sleep')
    def test_displays_multiple_retry_messages(self, mock_sleep):
        """Should display message for each retry attempt."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            {"status": "ok"},
        ])
        messages = []

        def on_retry(attempt, max_attempts, error):
            messages.append(f"Connection lost. Retrying... (attempt {attempt}/{max_attempts})")

        config = RetryConfig(max_retries=5, on_retry=on_retry)
        result = with_retry(mock_func, config)

        assert result == {"status": "ok"}
        assert len(messages) == 3
        assert messages[0] == "Connection lost. Retrying... (attempt 2/5)"
        assert messages[1] == "Connection lost. Retrying... (attempt 3/5)"
        assert messages[2] == "Connection lost. Retrying... (attempt 4/5)"


class TestRetryableExceptions:
    """Test the RETRYABLE_EXCEPTIONS tuple."""

    def test_includes_connect_error(self):
        """ConnectError should be in retryable exceptions."""
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS

    def test_includes_timeout_exception(self):
        """TimeoutException should be in retryable exceptions."""
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS

    def test_includes_connect_timeout(self):
        """ConnectTimeout should be in retryable exceptions."""
        assert httpx.ConnectTimeout in RETRYABLE_EXCEPTIONS

    def test_includes_read_timeout(self):
        """ReadTimeout should be in retryable exceptions."""
        assert httpx.ReadTimeout in RETRYABLE_EXCEPTIONS

    def test_includes_pool_timeout(self):
        """PoolTimeout should be in retryable exceptions."""
        assert httpx.PoolTimeout in RETRYABLE_EXCEPTIONS


class TestDefaultRetryCallback:
    """Test the default retry callback for CLI output."""

    @patch('rgrid.network_retry.console')
    def test_displays_connection_lost_message(self, mock_console):
        """Should display 'Connection lost. Retrying...' message."""
        default_retry_callback(2, 5, httpx.ConnectError("Connection refused"))

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Connection lost" in call_args
        assert "Retrying" in call_args
        assert "attempt 2/5" in call_args

    @patch('rgrid.network_retry.console')
    def test_displays_correct_attempt_numbers(self, mock_console):
        """Should display correct attempt numbers."""
        default_retry_callback(3, 5, httpx.ReadTimeout("Read timeout"))

        call_args = mock_console.print.call_args[0][0]
        assert "attempt 3/5" in call_args


class TestCreateApiWrapper:
    """Test the API wrapper factory function."""

    @patch('time.sleep')
    def test_wrapper_retries_on_connect_error(self, mock_sleep):
        """Wrapper should retry on ConnectError."""
        mock_func = Mock(side_effect=[
            httpx.ConnectError("Connection refused"),
            {"status": "ok"},
        ])

        with patch('rgrid.network_retry.console'):
            wrapped = create_api_wrapper(mock_func)
            result = wrapped()

        assert result == {"status": "ok"}
        assert mock_func.call_count == 2

    @patch('time.sleep')
    def test_wrapper_passes_arguments(self, mock_sleep):
        """Wrapper should pass arguments to the underlying function."""
        mock_func = Mock(return_value={"id": "123"})

        with patch('rgrid.network_retry.console'):
            wrapped = create_api_wrapper(mock_func)
            result = wrapped("arg1", kwarg1="value1")

        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        assert result == {"id": "123"}

    @patch('time.sleep')
    def test_wrapper_raises_network_error_on_persistent_failure(self, mock_sleep):
        """Wrapper should raise NetworkError after exhausting retries."""
        from rgrid_common.errors import NetworkError

        mock_func = Mock(side_effect=httpx.ConnectError("Connection refused"))

        with patch('rgrid.network_retry.console'):
            wrapped = create_api_wrapper(mock_func, max_retries=2)
            with pytest.raises(NetworkError) as exc_info:
                wrapped()

        assert "Network error" in str(exc_info.value.message)
        assert "Check connection and retry" in str(exc_info.value.message)

    @patch('time.sleep')
    def test_wrapper_does_not_retry_validation_errors(self, mock_sleep):
        """Wrapper should not retry on HTTP 400 validation errors."""
        request = httpx.Request("POST", "http://test.com")
        response = httpx.Response(400, request=request)
        error = httpx.HTTPStatusError("Bad request", request=request, response=response)
        mock_func = Mock(side_effect=error)

        with patch('rgrid.network_retry.console'):
            wrapped = create_api_wrapper(mock_func)
            with pytest.raises(httpx.HTTPStatusError):
                wrapped()

        assert mock_func.call_count == 1


class TestNetworkErrorMessage:
    """Test that the persistent failure message matches acceptance criteria."""

    @patch('time.sleep')
    def test_persistent_failure_message(self, mock_sleep):
        """On persistent failure, should display 'Network error. Check connection and retry.'"""
        from rgrid_common.errors import NetworkError

        mock_func = Mock(side_effect=httpx.ConnectError("Connection refused"))

        with patch('rgrid.network_retry.console'):
            wrapped = create_api_wrapper(mock_func, max_retries=1)
            with pytest.raises(NetworkError) as exc_info:
                wrapped()

        # Acceptance criteria: "Network error. Check connection and retry."
        assert "Network error" in exc_info.value.message
        assert "Check connection and retry" in exc_info.value.message
