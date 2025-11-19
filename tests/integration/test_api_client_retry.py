"""
Integration tests for API client retry logic (Story 10-5).

Tests that the API client properly retries on network failures.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
from rgrid.api_client import APIClient


class TestAPIClientRetry:
    """Test API client retry behavior with real network scenarios."""

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    def test_create_execution_retries_on_connection_error(
        self, mock_httpx_client, mock_load_creds
    ):
        """Test that create_execution retries on connection errors."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to fail twice then succeed
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.json.return_value = {"execution_id": "test_123"}
        mock_response.raise_for_status = Mock()

        mock_client_instance.post.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            mock_response
        ]

        # Create client and make request
        with patch('time.sleep'):  # Speed up test by mocking sleep
            client = APIClient()
            result = client.create_execution(script_content="print('hello')")

        # Verify it succeeded after retries
        assert result["execution_id"] == "test_123"
        # Should have tried 3 times (initial + 2 retries)
        assert mock_client_instance.post.call_count == 3

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    def test_get_execution_retries_on_timeout(
        self, mock_httpx_client, mock_load_creds
    ):
        """Test that get_execution retries on timeout errors."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to timeout once then succeed
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.json.return_value = {"status": "completed"}
        mock_response.raise_for_status = Mock()

        mock_client_instance.get.side_effect = [
            httpx.TimeoutException("Request timed out"),
            mock_response
        ]

        # Create client and make request
        with patch('time.sleep'):  # Speed up test by mocking sleep
            client = APIClient()
            result = client.get_execution("test_123")

        # Verify it succeeded after retry
        assert result["status"] == "completed"
        # Should have tried 2 times (initial + 1 retry)
        assert mock_client_instance.get.call_count == 2

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    def test_create_execution_retries_on_5xx_error(
        self, mock_httpx_client, mock_load_creds
    ):
        """Test that create_execution retries on 5xx server errors."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to fail with 503 then succeed
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        # Create 503 error response
        error_response = Mock()
        error_response.status_code = 503
        error = httpx.HTTPStatusError(
            "Service Unavailable",
            request=Mock(),
            response=error_response
        )

        # Success response
        success_response = Mock()
        success_response.json.return_value = {"execution_id": "test_456"}
        success_response.raise_for_status = Mock()

        mock_client_instance.post.side_effect = [
            error,
            success_response
        ]

        # Create client and make request
        with patch('time.sleep'):  # Speed up test by mocking sleep
            client = APIClient()
            result = client.create_execution(script_content="print('hello')")

        # Verify it succeeded after retry
        assert result["execution_id"] == "test_456"
        # Should have tried 2 times (initial + 1 retry)
        assert mock_client_instance.post.call_count == 2

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    def test_get_execution_does_not_retry_on_4xx_error(
        self, mock_httpx_client, mock_load_creds
    ):
        """Test that get_execution does NOT retry on 4xx client errors."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to fail with 404
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        # Create 404 error response
        error_response = Mock()
        error_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=error_response
        )

        mock_client_instance.get.side_effect = error

        # Create client and make request
        with patch('time.sleep'):  # Speed up test by mocking sleep
            client = APIClient()
            with pytest.raises(httpx.HTTPStatusError):
                client.get_execution("nonexistent")

        # Should have tried only once (no retries on 4xx)
        assert mock_client_instance.get.call_count == 1

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    def test_get_batch_status_fails_after_max_retries(
        self, mock_httpx_client, mock_load_creds
    ):
        """Test that get_batch_status fails after max retries exceeded."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to always fail
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        mock_client_instance.get.side_effect = httpx.ConnectError("Connection failed")

        # Create client and make request
        with patch('time.sleep'):  # Speed up test by mocking sleep
            with patch('click.echo'):  # Suppress error messages
                client = APIClient()
                with pytest.raises(httpx.ConnectError):
                    client.get_batch_status("test_batch")

        # Should have tried 6 times (initial + 5 retries)
        assert mock_client_instance.get.call_count == 6

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    @patch('time.sleep')
    @patch('click.echo')
    def test_retry_displays_user_messages(
        self, mock_echo, mock_sleep, mock_httpx_client, mock_load_creds
    ):
        """Test that retry displays user-friendly messages."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to fail once then succeed
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.json.return_value = {"artifacts": []}
        mock_response.raise_for_status = Mock()

        mock_client_instance.get.side_effect = [
            httpx.ConnectError("Connection failed"),
            mock_response
        ]

        # Create client and make request
        client = APIClient()
        result = client.get_artifacts("test_123")

        # Verify retry message was displayed
        assert mock_echo.call_count >= 1
        calls_str = [str(call) for call in mock_echo.call_args_list]
        assert any("retrying" in str(call).lower() for call in calls_str)
        assert any("attempt" in str(call).lower() for call in calls_str)

    @patch('rgrid.config.config.load_credentials')
    @patch('httpx.Client')
    @patch('time.sleep')
    def test_exponential_backoff_delays(
        self, mock_sleep, mock_httpx_client, mock_load_creds
    ):
        """Test that exponential backoff delays are correct."""
        # Setup credentials
        mock_load_creds.return_value = {
            "api_url": "https://api.rgrid.dev",
            "api_key": "test_key"
        }

        # Setup mock client to fail 3 times then succeed
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.json.return_value = {"execution_id": "test_789"}
        mock_response.raise_for_status = Mock()

        mock_client_instance.post.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            mock_response
        ]

        # Create client and make request
        with patch('click.echo'):  # Suppress messages
            client = APIClient()
            result = client.create_execution(script_content="print('test')")

        # Verify exponential backoff delays: 2s, 4s, 8s
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 2
        assert mock_sleep.call_args_list[1][0][0] == 4
        assert mock_sleep.call_args_list[2][0][0] == 8
