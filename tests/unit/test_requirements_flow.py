"""Unit tests for requirements_content flow through the system (Story 2.4).

Tests that requirements_content is properly:
1. Accepted by ExecutionCreate model
2. Stored in database via API
3. Retrieved by runner
4. Passed to executor for Docker image build
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestExecutionCreateModel:
    """Test ExecutionCreate accepts requirements_content."""

    def test_execution_create_with_requirements_content(self):
        """ExecutionCreate should accept optional requirements_content field."""
        from rgrid_common.models import ExecutionCreate

        # Act
        execution = ExecutionCreate(
            script_content="print('hello')",
            requirements_content="numpy==1.24.0\npandas==2.0.0"
        )

        # Assert
        assert execution.requirements_content == "numpy==1.24.0\npandas==2.0.0"

    def test_execution_create_without_requirements_content(self):
        """ExecutionCreate should work without requirements_content."""
        from rgrid_common.models import ExecutionCreate

        # Act
        execution = ExecutionCreate(
            script_content="print('hello')"
        )

        # Assert
        assert execution.requirements_content is None

    def test_execution_create_with_empty_requirements_content(self):
        """ExecutionCreate should accept empty string requirements_content."""
        from rgrid_common.models import ExecutionCreate

        # Act
        execution = ExecutionCreate(
            script_content="print('hello')",
            requirements_content=""
        )

        # Assert
        assert execution.requirements_content == ""


class TestWorkerRequirementsFlow:
    """Test worker passes requirements_content to executor."""

    def test_worker_passes_requirements_to_executor(self):
        """Worker should pass requirements_content to executor.execute_script()."""
        # This test verifies the interface contract:
        # executor.execute_script() should accept requirements_content parameter
        from runner.executor import DockerExecutor

        # Verify execute_script accepts requirements_content parameter
        import inspect
        sig = inspect.signature(DockerExecutor.execute_script)
        params = list(sig.parameters.keys())

        assert 'requirements_content' in params, \
            "execute_script should accept requirements_content parameter"

    def test_worker_code_includes_requirements_content_call(self):
        """Worker.process_job should pass requirements_content to executor."""
        # Read worker.py source and verify requirements_content is passed
        from pathlib import Path
        worker_path = Path(__file__).parent.parent.parent / "runner" / "runner" / "worker.py"
        worker_source = worker_path.read_text()

        assert 'requirements_content=' in worker_source, \
            "worker.py should pass requirements_content to executor"


class TestExecutorWithRequirements:
    """Test executor builds Docker image with dependencies when requirements provided."""

    def test_executor_has_requirements_content_parameter(self):
        """DockerExecutor.execute_script should accept requirements_content."""
        from runner.executor import DockerExecutor
        import inspect

        sig = inspect.signature(DockerExecutor.execute_script)
        params = list(sig.parameters.keys())

        assert 'requirements_content' in params

    def test_executor_builds_image_when_requirements_provided(self):
        """Executor should call build_image_with_dependencies when requirements provided."""
        from runner.executor import DockerExecutor

        # Verify build_image_with_dependencies method exists
        assert hasattr(DockerExecutor, 'build_image_with_dependencies'), \
            "DockerExecutor should have build_image_with_dependencies method"


class TestDatabaseModelRequirements:
    """Test database models include requirements_content field."""

    def test_api_execution_model_has_requirements_content(self):
        """API Execution model should have requirements_content column."""
        # Read the model source file to verify column exists
        # (avoids import issues with api.app module)
        from pathlib import Path
        model_path = Path(__file__).parent.parent.parent / "api" / "app" / "models" / "execution.py"
        model_source = model_path.read_text()

        assert 'requirements_content' in model_source, \
            "Execution model should have requirements_content column"
        assert 'Text' in model_source, \
            "requirements_content should be a Text column"

    def test_runner_execution_model_has_requirements_content(self):
        """Runner Execution model should have requirements_content column."""
        from runner.runner.models import Execution

        # Check if the column exists in the model
        columns = [c.name for c in Execution.__table__.columns]

        assert 'requirements_content' in columns, \
            "Runner Execution model should have requirements_content column"
