"""Unit tests for structured error handling (Tier 3 - Story 10-4).

These tests verify that RGrid's structured error types have correct fields,
serialize properly, and provide helpful context to users.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
import os

# Imports set up by conftest.py (Story 10-4)
from api.errors import (
    RGridError,
    ValidationError,
    ExecutionError,
    TimeoutError,
    NetworkError
)
from rgrid.errors import display_error


class TestRGridBaseError:
    """Test the base RGridError class."""

    def test_base_error_has_required_fields(self):
        """Base error should have message, context, and timestamp."""
        # Arrange & Act
        error = RGridError("Test error", context={"key": "value"})

        # Assert
        assert error.message == "Test error"
        assert error.context == {"key": "value"}
        assert isinstance(error.timestamp, datetime)

    def test_base_error_context_defaults_to_empty_dict(self):
        """When no context provided, should default to empty dict."""
        # Arrange & Act
        error = RGridError("Test error")

        # Assert
        assert error.context == {}

    def test_base_error_to_dict(self):
        """Base error should serialize to dict with all fields."""
        # Arrange
        error = RGridError("Test error", context={"file": "test.py"})

        # Act
        result = error.to_dict()

        # Assert
        assert result["error_type"] == "RGridError"
        assert result["message"] == "Test error"
        assert result["context"] == {"file": "test.py"}
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)


class TestValidationError:
    """Test the ValidationError class for user input validation."""

    def test_validation_error_format(self):
        """ValidationError should have correct fields and suggestions."""
        # Arrange & Act
        error = ValidationError(
            "Script file not found",
            context={"file": "nonexistent.py", "location": "/home/user"}
        )

        # Assert
        assert error.message == "Script file not found"
        assert error.context["file"] == "nonexistent.py"
        assert error.context["location"] == "/home/user"
        assert hasattr(error, 'suggestions')
        assert len(error.suggestions) > 0

    def test_validation_error_to_dict(self):
        """ValidationError should serialize correctly."""
        # Arrange
        error = ValidationError("Invalid input", context={"param": "timeout"})

        # Act
        result = error.to_dict()

        # Assert
        assert result["error_type"] == "ValidationError"
        assert result["message"] == "Invalid input"


class TestExecutionError:
    """Test the ExecutionError class for script execution errors."""

    def test_execution_error_format(self):
        """ExecutionError should include execution context."""
        # Arrange & Act
        error = ExecutionError(
            "Script exited with non-zero status",
            context={
                "exec_id": "exec-123",
                "exit_code": 1,
                "script": "process.py"
            }
        )

        # Assert
        assert error.message == "Script exited with non-zero status"
        assert error.context["exec_id"] == "exec-123"
        assert error.context["exit_code"] == 1
        assert hasattr(error, 'suggestions')

    def test_execution_error_to_json(self):
        """ExecutionError should be JSON serializable."""
        # Arrange
        error = ExecutionError("Execution failed", context={"exec_id": "exec-456"})

        # Act
        error_dict = error.to_dict()
        json_str = json.dumps(error_dict)

        # Assert
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["error_type"] == "ExecutionError"


class TestTimeoutError:
    """Test the TimeoutError class for job timeout errors."""

    def test_timeout_error_format(self):
        """TimeoutError should show duration and elapsed time."""
        # Arrange & Act
        error = TimeoutError(
            "Execution timed out after 60 seconds",
            context={
                "exec_id": "exec-789",
                "timeout": 60,
                "elapsed": 61
            }
        )

        # Assert
        assert "60 seconds" in error.message
        assert error.context["timeout"] == 60
        assert error.context["elapsed"] == 61
        assert hasattr(error, 'suggestions')
        assert any("timeout" in s.lower() for s in error.suggestions)


class TestNetworkError:
    """Test the NetworkError class for API/network communication errors."""

    def test_network_error_format(self):
        """NetworkError should include endpoint information."""
        # Arrange & Act
        error = NetworkError(
            "Failed to connect to API",
            context={
                "endpoint": "https://api.rgrid.io/v1/jobs",
                "status_code": 503
            }
        )

        # Assert
        assert error.message == "Failed to connect to API"
        assert error.context["endpoint"] == "https://api.rgrid.io/v1/jobs"
        assert error.context["status_code"] == 503
        assert hasattr(error, 'suggestions')


class TestCLIErrorDisplay:
    """Test the CLI error display formatter."""

    @patch('rgrid.errors.click.echo')
    def test_cli_error_display(self, mock_echo):
        """CLI should format errors with emoji and context."""
        # Arrange
        error = ValidationError(
            "Script file not found",
            context={"file": "test.py", "location": "/home/user"}
        )

        # Act
        display_error(error)

        # Assert
        # Check that echo was called multiple times
        assert mock_echo.call_count >= 3

        # Get all the calls and check for key components
        all_calls = [str(call) for call in mock_echo.call_args_list]
        output = ' '.join(all_calls)

        # Should contain error type and message
        assert "Validation Error" in output or "ValidationError" in output
        assert "Script file not found" in output

    @patch('rgrid.errors.click.echo')
    def test_cli_displays_suggestions(self, mock_echo):
        """CLI should display suggestions if available."""
        # Arrange
        error = TimeoutError(
            "Execution timed out",
            context={"timeout": 30}
        )

        # Act
        display_error(error)

        # Assert
        all_calls = [str(call) for call in mock_echo.call_args_list]
        output = ' '.join(all_calls)

        # Should contain suggestions marker
        assert "Suggestions" in output or "💡" in output
