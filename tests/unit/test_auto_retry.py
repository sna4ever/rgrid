"""Unit tests for auto-retry transient failures (Story 10-7).

Tests the automatic retry mechanism for transient failures like worker crashes,
timeouts, and network errors.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestTransientErrorClassification:
    """Test transient error detection and classification."""

    def test_worker_death_is_transient(self):
        """Worker death should be classified as transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("Worker died unexpectedly", exit_code=-1) is True

    def test_worker_rescheduled_is_transient(self):
        """Rescheduled worker error should be transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("Worker worker-123 died - rescheduled", exit_code=-1) is True

    def test_timeout_is_transient(self):
        """Execution timeout should be transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("Execution timeout (60s) or error occurred", exit_code=-1) is True

    def test_oom_killed_is_transient(self):
        """OOM killed should be transient (may succeed on another worker)."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("Killed", exit_code=-1) is True

    def test_memory_error_is_transient(self):
        """MemoryError should be transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("MemoryError: Unable to allocate", exit_code=-1) is True

    def test_script_error_is_not_transient(self):
        """Non-zero exit from user script should NOT be transient."""
        from rgrid_common.retry import is_transient_error

        # Exit code > 0 means script returned error (user's fault, not infrastructure)
        assert is_transient_error("Script failed", exit_code=1) is False
        assert is_transient_error("ModuleNotFoundError: No module named 'foo'", exit_code=1) is False

    def test_syntax_error_is_not_transient(self):
        """Syntax errors are permanent, not transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error("SyntaxError: invalid syntax", exit_code=1) is False

    def test_none_error_with_zero_exit_is_not_transient(self):
        """Successful execution (exit_code=0) should not be transient."""
        from rgrid_common.retry import is_transient_error

        assert is_transient_error(None, exit_code=0) is False
        assert is_transient_error("", exit_code=0) is False


class TestAutoRetryLogic:
    """Test the auto-retry decision logic."""

    def test_should_retry_when_transient_and_under_limit(self):
        """Should retry if error is transient and retry_count < max_retries."""
        from rgrid_common.retry import should_auto_retry

        assert should_auto_retry(
            error_message="Worker died unexpectedly",
            exit_code=-1,
            retry_count=0,
            max_retries=2,
        ) is True

        assert should_auto_retry(
            error_message="Worker died unexpectedly",
            exit_code=-1,
            retry_count=1,
            max_retries=2,
        ) is True

    def test_should_not_retry_when_max_reached(self):
        """Should not retry if retry_count >= max_retries."""
        from rgrid_common.retry import should_auto_retry

        assert should_auto_retry(
            error_message="Worker died unexpectedly",
            exit_code=-1,
            retry_count=2,
            max_retries=2,
        ) is False

    def test_should_not_retry_permanent_error(self):
        """Should not retry permanent errors (script failures)."""
        from rgrid_common.retry import should_auto_retry

        assert should_auto_retry(
            error_message="ModuleNotFoundError",
            exit_code=1,
            retry_count=0,
            max_retries=2,
        ) is False

    def test_should_not_retry_on_success(self):
        """Should not retry successful executions."""
        from rgrid_common.retry import should_auto_retry

        assert should_auto_retry(
            error_message=None,
            exit_code=0,
            retry_count=0,
            max_retries=2,
        ) is False


class TestRetryMessageFormatting:
    """Test retry status message formatting."""

    def test_format_retry_message(self):
        """Should format retry message with count."""
        from rgrid_common.retry import format_retry_message

        msg = format_retry_message(
            retry_count=1,
            max_retries=2,
            reason="worker failure",
        )
        assert "Auto-retry 1/2" in msg
        assert "worker failure" in msg

    def test_format_max_retries_exceeded_message(self):
        """Should format max retries exceeded message."""
        from rgrid_common.retry import format_max_retries_message

        msg = format_max_retries_message(max_retries=2, original_error="Worker died")
        assert "Max retries" in msg or "2" in msg


class TestExecutionModelRetryFields:
    """Test that execution model has retry tracking fields."""

    def test_execution_has_retry_fields(self):
        """Execution model should have retry tracking fields."""
        from app.models.execution import Execution

        # Check that the class has these attributes defined
        mapper = Execution.__mapper__
        columns = {c.name for c in mapper.columns}

        assert "retry_count" in columns, "Missing retry_count field"
        assert "max_retries" in columns, "Missing max_retries field"

    def test_default_retry_values(self):
        """Retry fields should have sensible defaults when explicitly set."""
        from app.models.execution import Execution

        # Create instance with explicit values (database defaults apply at DB level)
        exec_instance = Execution(
            execution_id="test_exec",
            script_content="print('test')",
            runtime="python:3.11",
            status="queued",
            retry_count=0,
            max_retries=2,
        )

        assert exec_instance.retry_count == 0
        assert exec_instance.max_retries == 2
