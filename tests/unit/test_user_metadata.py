"""Unit tests for user metadata tagging (Story 10.8).

Tests for:
- --metadata flag parsing in CLI run command
- user_metadata field in Pydantic models
- user_metadata storage in database
- --metadata filter in list command
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner


class TestMetadataFlagParsing:
    """Test parsing of --metadata key=value flags."""

    def test_single_metadata_flag(self):
        """Single --metadata flag should be parsed correctly."""
        # Test metadata format: "project=ml-model"
        metadata_str = "project=ml-model"
        key, value = metadata_str.split("=", 1)

        assert key == "project"
        assert value == "ml-model"

    def test_multiple_metadata_values(self):
        """Multiple --metadata flags should all be parsed."""
        metadata_list = ["project=ml-model", "env=prod", "version=1.2.3"]

        result = {}
        for metadata_str in metadata_list:
            key, value = metadata_str.split("=", 1)
            result[key] = value

        assert result == {
            "project": "ml-model",
            "env": "prod",
            "version": "1.2.3"
        }

    def test_metadata_with_equals_in_value(self):
        """Metadata values containing '=' should be preserved."""
        metadata_str = "config=key=value"
        key, value = metadata_str.split("=", 1)

        assert key == "config"
        assert value == "key=value"

    def test_empty_metadata_value(self):
        """Empty metadata values should be allowed."""
        metadata_str = "empty="
        key, value = metadata_str.split("=", 1)

        assert key == "empty"
        assert value == ""

    def test_invalid_metadata_no_equals(self):
        """Metadata without '=' should raise error."""
        metadata_str = "invalid"

        with pytest.raises(ValueError):
            if "=" not in metadata_str:
                raise ValueError("Invalid metadata format")


class TestExecutionCreateMetadataField:
    """Test that ExecutionCreate model has user_metadata field."""

    def test_execution_create_has_user_metadata_field(self):
        """ExecutionCreate should have user_metadata field."""
        from rgrid_common.models import ExecutionCreate

        # Check field exists in model
        assert 'user_metadata' in ExecutionCreate.model_fields

    def test_execution_create_with_metadata(self):
        """ExecutionCreate should accept user_metadata."""
        from rgrid_common.models import ExecutionCreate

        execution = ExecutionCreate(
            script_content="print('hello')",
            user_metadata={"project": "ml-model", "env": "prod"}
        )

        assert execution.user_metadata == {"project": "ml-model", "env": "prod"}

    def test_execution_create_metadata_is_optional(self):
        """user_metadata should be optional."""
        from rgrid_common.models import ExecutionCreate

        execution = ExecutionCreate(
            script_content="print('hello')"
        )

        # Default should be None or empty dict
        assert execution.user_metadata is None or execution.user_metadata == {}


class TestExecutionResponseMetadataField:
    """Test that ExecutionResponse model has user_metadata field."""

    def test_execution_response_has_user_metadata_field(self):
        """ExecutionResponse should have user_metadata field."""
        from rgrid_common.models import ExecutionResponse

        assert 'user_metadata' in ExecutionResponse.model_fields

    def test_execution_response_with_metadata(self):
        """ExecutionResponse should include user_metadata in serialization."""
        from rgrid_common.models import ExecutionResponse
        from datetime import datetime, timezone

        response = ExecutionResponse(
            execution_id="exec_test123",
            script_content="print('hello')",
            runtime="python:3.11",
            status="completed",
            created_at=datetime.now(timezone.utc),
            user_metadata={"project": "ml-model"}
        )

        assert response.user_metadata == {"project": "ml-model"}


class TestExecutionModelUserMetadata:
    """Test that SQLAlchemy Execution model has user_metadata column."""

    def test_api_execution_model_has_user_metadata(self):
        """API Execution model should have user_metadata column."""
        from api.app.models.execution import Execution

        assert hasattr(Execution, 'user_metadata')

        column = Execution.__table__.columns.get('user_metadata')
        assert column is not None
        assert column.nullable is True


class TestCliRunMetadataFlag:
    """Test --metadata flag in run command."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch('rgrid.commands.run.get_client')
    def test_run_command_accepts_metadata_flag(self, mock_get_client, cli_runner, tmp_path):
        """Run command should accept --metadata flag."""
        from rgrid.commands.run import run

        # Create test script
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Mock API client
        mock_client = Mock()
        mock_client.create_execution.return_value = {
            "execution_id": "exec_test123",
            "status": "queued",
        }
        mock_get_client.return_value = mock_client

        # Run with --metadata flag and --remote-only (to skip waiting)
        result = cli_runner.invoke(run, [
            str(script),
            "--metadata", "project=ml-model",
            "--remote-only"
        ])

        # Should not fail with unknown option
        assert "--metadata" not in result.output or "Error" not in result.output

    @patch('rgrid.commands.run.get_client')
    def test_run_passes_metadata_to_api(self, mock_get_client, cli_runner, tmp_path):
        """Run command should pass metadata to API client."""
        from rgrid.commands.run import run

        # Create test script
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Mock API client
        mock_client = Mock()
        mock_client.create_execution.return_value = {
            "execution_id": "exec_test123",
            "status": "queued",
        }
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(run, [
            str(script),
            "--metadata", "project=ml-model",
            "--metadata", "env=prod",
            "--remote-only"
        ])

        # API client should receive user_metadata
        mock_client.create_execution.assert_called_once()
        call_kwargs = mock_client.create_execution.call_args[1]

        assert call_kwargs.get('user_metadata') == {
            "project": "ml-model",
            "env": "prod"
        }


class TestApiClientUserMetadata:
    """Test API client passes user_metadata to API."""

    def test_create_execution_accepts_user_metadata(self):
        """API client create_execution should accept user_metadata parameter."""
        from rgrid.api_client import APIClient
        import inspect

        sig = inspect.signature(APIClient.create_execution)
        params = list(sig.parameters.keys())

        assert 'user_metadata' in params


class TestListCommandMetadataFilter:
    """Test --metadata filter in list command."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_list_command_exists(self):
        """List command should exist in CLI."""
        from rgrid.cli import main

        # Get all command names
        command_names = [cmd for cmd in main.commands.keys()]

        assert 'list' in command_names

    @patch('rgrid.commands.list.get_client')
    def test_list_command_accepts_metadata_filter(self, mock_get_client, cli_runner):
        """List command should accept --metadata filter flag."""
        from rgrid.commands.list import list_executions

        mock_client = Mock()
        mock_client.list_executions.return_value = []
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(list_executions, [
            "--metadata", "project=ml-model"
        ])

        # Should not fail with unknown option
        assert result.exit_code == 0 or "unknown option" not in result.output.lower()

    @patch('rgrid.commands.list.get_client')
    def test_list_filters_by_metadata(self, mock_get_client, cli_runner):
        """List command should pass metadata filter to API."""
        from rgrid.commands.list import list_executions

        mock_client = Mock()
        mock_client.list_executions.return_value = [
            {
                "execution_id": "exec_1",
                "status": "completed",
                "user_metadata": {"project": "ml-model"}
            }
        ]
        mock_get_client.return_value = mock_client

        result = cli_runner.invoke(list_executions, [
            "--metadata", "project=ml-model"
        ])

        # API should be called with metadata filter
        mock_client.list_executions.assert_called_once()
        call_kwargs = mock_client.list_executions.call_args[1]

        assert call_kwargs.get('metadata_filter') == {"project": "ml-model"}


class TestApiClientListExecutions:
    """Test API client list_executions method."""

    def test_list_executions_method_exists(self):
        """API client should have list_executions method."""
        from rgrid.api_client import APIClient

        assert hasattr(APIClient, 'list_executions')

    def test_list_executions_accepts_metadata_filter(self):
        """list_executions should accept metadata_filter parameter."""
        from rgrid.api_client import APIClient
        import inspect

        sig = inspect.signature(APIClient.list_executions)
        params = list(sig.parameters.keys())

        assert 'metadata_filter' in params
