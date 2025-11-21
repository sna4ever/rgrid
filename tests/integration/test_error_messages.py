"""Integration tests for error messages (Tier 3 - Story 10-4).

These tests verify end-to-end error handling for common user scenarios,
ensuring that helpful error messages are shown for typical mistakes.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Skip entire module - api.errors not yet implemented (Story 10-4)
pytest.importorskip("api.errors", reason="api.errors module not yet implemented (Story 10-4)")

from rgrid.errors import display_error
from api.errors import ValidationError, ExecutionError, TimeoutError, NetworkError


class TestMissingFileErrorMessage:
    """Test error messages when script file is not found."""

    def test_missing_file_error_message(self):
        """File not found should show helpful message with file path and suggestions."""
        # Arrange
        nonexistent_file = "nonexistent.py"
        error = ValidationError(
            "Script file not found",
            context={
                "file": nonexistent_file,
                "location": os.getcwd()
            }
        )

        # Act
        error_dict = error.to_dict()

        # Assert
        assert error_dict["error_type"] == "ValidationError"
        assert "not found" in error_dict["message"].lower()
        assert error_dict["context"]["file"] == nonexistent_file
        assert hasattr(error, 'suggestions')
        assert len(error.suggestions) > 0

    @patch('rgrid.errors.click.echo')
    def test_missing_file_cli_display(self, mock_echo):
        """CLI should display missing file error in friendly format."""
        # Arrange
        error = ValidationError(
            "Script file not found",
            context={"file": "missing.py", "location": "/home/user"}
        )

        # Act
        display_error(error)

        # Assert
        # Get all echo calls - some use keyword args, some positional
        all_calls = []
        for call in mock_echo.call_args_list:
            if call.args:
                all_calls.append(str(call.args[0]))
            elif 'err' in call.kwargs or len(call.kwargs) > 0:
                # Handle calls with only keyword arguments
                for value in call.kwargs.values():
                    if isinstance(value, str):
                        all_calls.append(value)

        all_output = ' '.join(all_calls)
        assert "Validation Error" in all_output or "ValidationError" in all_output
        assert "missing.py" in all_output


class TestInvalidRuntimeErrorMessage:
    """Test error messages when invalid runtime is specified."""

    def test_invalid_runtime_error_message(self):
        """Invalid runtime should suggest available alternatives."""
        # Arrange
        invalid_runtime = "ruby3.0"
        available_runtimes = ["python3.11", "python3.12", "node20", "node22"]

        error = ValidationError(
            f"Invalid runtime: {invalid_runtime}",
            context={
                "requested": invalid_runtime,
                "available": available_runtimes
            }
        )

        # Act
        error_dict = error.to_dict()

        # Assert
        assert error_dict["error_type"] == "ValidationError"
        assert invalid_runtime in error_dict["message"]
        assert error_dict["context"]["requested"] == invalid_runtime
        assert error_dict["context"]["available"] == available_runtimes

    @patch('rgrid.errors.click.echo')
    def test_invalid_runtime_cli_suggestions(self, mock_echo):
        """CLI should show available runtimes when invalid one is requested."""
        # Arrange
        error = ValidationError(
            "Invalid runtime: ruby3.0",
            context={
                "requested": "ruby3.0",
                "available": ["python3.11", "node20"]
            }
        )

        # Act
        display_error(error)

        # Assert
        # Get all echo calls - some use keyword args, some positional
        all_calls = []
        for call in mock_echo.call_args_list:
            if call.args:
                all_calls.append(str(call.args[0]))
            elif 'err' in call.kwargs or len(call.kwargs) > 0:
                # Handle calls with only keyword arguments
                for value in call.kwargs.values():
                    if isinstance(value, str):
                        all_calls.append(value)

        all_output = ' '.join(all_calls)
        assert "ruby3.0" in all_output
        assert "python3.11" in all_output or "available" in all_output.lower()


class TestTimeoutErrorMessage:
    """Test error messages when job times out."""

    def test_timeout_error_message(self):
        """Timeout should show duration and suggestion to increase timeout."""
        # Arrange
        timeout_seconds = 60
        elapsed_seconds = 61

        error = TimeoutError(
            f"Execution timed out after {timeout_seconds} seconds",
            context={
                "exec_id": "exec-123",
                "timeout": timeout_seconds,
                "elapsed": elapsed_seconds
            }
        )

        # Act
        error_dict = error.to_dict()

        # Assert
        assert error_dict["error_type"] == "TimeoutError"
        assert str(timeout_seconds) in error_dict["message"]
        assert error_dict["context"]["timeout"] == timeout_seconds
        assert error_dict["context"]["elapsed"] == elapsed_seconds

    @patch('rgrid.errors.click.echo')
    def test_timeout_cli_shows_suggestion(self, mock_echo):
        """CLI should suggest increasing timeout or optimizing script."""
        # Arrange
        error = TimeoutError(
            "Execution timed out after 30 seconds",
            context={"timeout": 30, "elapsed": 31}
        )

        # Act
        display_error(error)

        # Assert
        # Get all echo calls - some use keyword args, some positional
        all_calls = []
        for call in mock_echo.call_args_list:
            if call.args:
                all_calls.append(str(call.args[0]))
            elif 'err' in call.kwargs or len(call.kwargs) > 0:
                # Handle calls with only keyword arguments
                for value in call.kwargs.values():
                    if isinstance(value, str):
                        all_calls.append(value)

        all_output = ' '.join(all_calls)

        # Check suggestions are displayed
        assert "Suggestions" in all_output or "💡" in all_output

        # The actual suggestions come from the error class
        suggestions_text = ' '.join(error.suggestions)
        assert "timeout" in suggestions_text.lower() or "faster" in suggestions_text.lower()


class TestNetworkErrorMessage:
    """Test error messages when network/API communication fails."""

    def test_network_error_message(self):
        """Network error should show endpoint and status code."""
        # Arrange
        endpoint = "https://api.rgrid.io/v1/jobs"
        status_code = 503

        error = NetworkError(
            "Failed to connect to API",
            context={
                "endpoint": endpoint,
                "status_code": status_code
            }
        )

        # Act
        error_dict = error.to_dict()

        # Assert
        assert error_dict["error_type"] == "NetworkError"
        assert "API" in error_dict["message"] or "connect" in error_dict["message"].lower()
        assert error_dict["context"]["endpoint"] == endpoint
        assert error_dict["context"]["status_code"] == status_code

    @patch('rgrid.errors.click.echo')
    def test_network_error_cli_display(self, mock_echo):
        """CLI should display network error with endpoint info."""
        # Arrange
        error = NetworkError(
            "Connection refused",
            context={
                "endpoint": "https://api.rgrid.io/v1/jobs",
                "error": "Connection refused"
            }
        )

        # Act
        display_error(error)

        # Assert
        # Get all echo calls - some use keyword args, some positional
        all_calls = []
        for call in mock_echo.call_args_list:
            if call.args:
                all_calls.append(str(call.args[0]))
            elif 'err' in call.kwargs or len(call.kwargs) > 0:
                # Handle calls with only keyword arguments
                for value in call.kwargs.values():
                    if isinstance(value, str):
                        all_calls.append(value)

        all_output = ' '.join(all_calls)
        assert "Network Error" in all_output or "NetworkError" in all_output
        assert "api.rgrid.io" in all_output
