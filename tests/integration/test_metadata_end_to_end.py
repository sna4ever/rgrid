"""Integration tests for execution metadata tagging (Story 10-8)."""

import pytest
from pathlib import Path
import tempfile
import os


class TestMetadataEndToEnd:
    """Test metadata tagging end-to-end flow."""

    @pytest.mark.asyncio
    async def test_create_execution_with_metadata(self, init_test_db):
        """Create execution with metadata and verify it's stored."""
        from app.database import get_db
        from app.models.execution import Execution
        from sqlalchemy import select
        from datetime import datetime

        # Create execution with metadata
        async for db in get_db():
            execution = Execution(
                execution_id="test_exec_001",
                script_content="print('hello')",
                runtime="python:3.11",
                args=[],
                env_vars={},
                status="queued",
                metadata={"project": "ml-model", "env": "prod"},
                created_at=datetime.utcnow()
            )
            db.add(execution)
            await db.commit()

            # Query back and verify metadata
            result = await db.execute(
                select(Execution).where(Execution.execution_id == "test_exec_001")
            )
            retrieved = result.scalar_one()

            assert retrieved.metadata == {"project": "ml-model", "env": "prod"}
            break

    @pytest.mark.asyncio
    async def test_filter_executions_by_single_metadata(self, init_test_db):
        """Filter executions by single metadata key=value."""
        from app.database import get_db
        from app.models.execution import Execution
        from sqlalchemy import select
        from datetime import datetime

        async for db in get_db():
            # Create multiple executions with different metadata
            executions = [
                Execution(
                    execution_id="exec_ml_001",
                    script_content="print('ml')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="queued",
                    metadata={"project": "ml-model", "env": "prod"},
                    created_at=datetime.utcnow()
                ),
                Execution(
                    execution_id="exec_etl_001",
                    script_content="print('etl')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="queued",
                    metadata={"project": "etl-pipeline", "env": "prod"},
                    created_at=datetime.utcnow()
                ),
                Execution(
                    execution_id="exec_ml_002",
                    script_content="print('ml2')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="queued",
                    metadata={"project": "ml-model", "env": "dev"},
                    created_at=datetime.utcnow()
                ),
            ]

            for exec in executions:
                db.add(exec)
            await db.commit()

            # Filter by project=ml-model
            # Using JSONB @> operator: WHERE metadata @> '{"project": "ml-model"}'::jsonb
            filter_value = {"project": "ml-model"}
            result = await db.execute(
                select(Execution).where(
                    Execution.metadata.contains(filter_value)
                )
            )
            filtered = result.scalars().all()

            # Should get 2 executions with project=ml-model
            assert len(filtered) == 2
            execution_ids = [e.execution_id for e in filtered]
            assert "exec_ml_001" in execution_ids
            assert "exec_ml_002" in execution_ids
            assert "exec_etl_001" not in execution_ids
            break

    @pytest.mark.asyncio
    async def test_filter_executions_by_multiple_metadata(self, init_test_db):
        """Filter executions by multiple metadata key=value pairs (AND logic)."""
        from app.database import get_db
        from app.models.execution import Execution
        from sqlalchemy import select
        from datetime import datetime

        async for db in get_db():
            # Create executions
            executions = [
                Execution(
                    execution_id="exec_ml_prod",
                    script_content="print('ml prod')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="queued",
                    metadata={"project": "ml-model", "env": "prod", "team": "ds"},
                    created_at=datetime.utcnow()
                ),
                Execution(
                    execution_id="exec_ml_dev",
                    script_content="print('ml dev')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="queued",
                    metadata={"project": "ml-model", "env": "dev", "team": "ds"},
                    created_at=datetime.utcnow()
                ),
            ]

            for exec in executions:
                db.add(exec)
            await db.commit()

            # Filter by project=ml-model AND env=prod
            filter_value = {"project": "ml-model", "env": "prod"}
            result = await db.execute(
                select(Execution).where(
                    Execution.metadata.contains(filter_value)
                )
            )
            filtered = result.scalars().all()

            # Should get only 1 execution matching both conditions
            assert len(filtered) == 1
            assert filtered[0].execution_id == "exec_ml_prod"
            break

    @pytest.mark.asyncio
    async def test_executions_without_metadata(self, init_test_db):
        """Executions without metadata should have empty JSON object."""
        from app.database import get_db
        from app.models.execution import Execution
        from sqlalchemy import select
        from datetime import datetime

        async for db in get_db():
            # Create execution without metadata
            execution = Execution(
                execution_id="exec_no_meta",
                script_content="print('no meta')",
                runtime="python:3.11",
                args=[],
                env_vars={},
                status="queued",
                created_at=datetime.utcnow()
            )
            db.add(execution)
            await db.commit()

            # Query back
            result = await db.execute(
                select(Execution).where(Execution.execution_id == "exec_no_meta")
            )
            retrieved = result.scalar_one()

            # Should have empty dict as metadata
            assert retrieved.metadata == {} or retrieved.metadata is None
            break

    def test_cli_run_with_metadata(self):
        """Test CLI run command with --metadata flags."""
        from click.testing import CliRunner
        from rgrid.cli import cli
        from unittest.mock import patch, Mock

        runner = CliRunner()

        # Create a temporary script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            script_path = f.name

        try:
            # Mock the API client
            with patch('rgrid.commands.run.get_client') as mock_get_client:
                mock_client = Mock()
                mock_client.create_execution.return_value = {
                    "execution_id": "exec_123",
                    "status": "queued",
                    "upload_urls": {},
                }
                mock_get_client.return_value = mock_client

                # Run with metadata
                result = runner.invoke(cli, [
                    'run',
                    script_path,
                    '--metadata', 'project=ml-model',
                    '--metadata', 'env=prod'
                ])

                # Verify command succeeded
                assert result.exit_code == 0

                # Verify API client was called with metadata
                mock_client.create_execution.assert_called_once()
                call_kwargs = mock_client.create_execution.call_args[1]
                assert call_kwargs['metadata'] == {"project": "ml-model", "env": "prod"}

        finally:
            os.unlink(script_path)

    def test_cli_list_with_metadata_filter(self):
        """Test CLI list command with --metadata filter."""
        from click.testing import CliRunner
        from rgrid.cli import cli
        from unittest.mock import patch, Mock

        runner = CliRunner()

        # Mock the API client
        with patch('rgrid.commands.list.get_client') as mock_get_client:
            mock_client = Mock()
            mock_client.list_executions.return_value = [
                {
                    "execution_id": "exec_001",
                    "status": "completed",
                    "metadata": {"project": "ml-model", "env": "prod"},
                    "created_at": "2025-01-01T00:00:00",
                },
                {
                    "execution_id": "exec_002",
                    "status": "completed",
                    "metadata": {"project": "ml-model", "env": "dev"},
                    "created_at": "2025-01-01T00:01:00",
                }
            ]
            mock_get_client.return_value = mock_client

            # Run list with metadata filter
            result = runner.invoke(cli, [
                'list',
                '--metadata', 'project=ml-model'
            ])

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify API client was called with metadata filter
            mock_client.list_executions.assert_called_once()
            call_kwargs = mock_client.list_executions.call_args[1]
            assert call_kwargs['metadata'] == {"project": "ml-model"}

            # Verify output contains execution IDs
            assert "exec_001" in result.output
            assert "exec_002" in result.output

    @pytest.mark.asyncio
    async def test_api_create_execution_with_metadata(self, init_test_db):
        """Test API endpoint for creating execution with metadata."""
        from fastapi.testclient import TestClient
        from app.main import app
        from unittest.mock import patch

        client = TestClient(app)

        # Mock API key verification
        with patch('app.api.v1.executions.verify_api_key', return_value="test_key"):
            response = client.post(
                "/api/v1/executions",
                json={
                    "script_content": "print('hello')",
                    "runtime": "python:3.11",
                    "args": [],
                    "env_vars": {},
                    "input_files": [],
                    "metadata": {"project": "ml-model", "env": "prod"}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "execution_id" in data
            assert data["metadata"] == {"project": "ml-model", "env": "prod"}

    @pytest.mark.asyncio
    async def test_api_list_executions_with_metadata_filter(self, init_test_db):
        """Test API endpoint for listing executions with metadata filter."""
        from fastapi.testclient import TestClient
        from app.main import app
        from unittest.mock import patch
        from app.database import get_db
        from app.models.execution import Execution
        from datetime import datetime

        # Create test executions
        async for db in get_db():
            executions = [
                Execution(
                    execution_id="exec_api_001",
                    script_content="print('test')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="completed",
                    metadata={"project": "ml-model"},
                    created_at=datetime.utcnow()
                ),
                Execution(
                    execution_id="exec_api_002",
                    script_content="print('test')",
                    runtime="python:3.11",
                    args=[],
                    env_vars={},
                    status="completed",
                    metadata={"project": "etl-pipeline"},
                    created_at=datetime.utcnow()
                ),
            ]
            for exec in executions:
                db.add(exec)
            await db.commit()
            break

        client = TestClient(app)

        # Mock API key verification
        with patch('app.api.v1.executions.verify_api_key', return_value="test_key"):
            response = client.get(
                "/api/v1/executions",
                params={"metadata": "project=ml-model"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["execution_id"] == "exec_api_001"
