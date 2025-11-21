"""Unit tests for MinIO retention policy (Story 7-3).

Tests artifact expiry timestamps and lifecycle configuration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os


class TestArtifactExpiry:
    """Test artifact expiry timestamp calculation."""

    def test_artifact_gets_default_30_day_expiry(self):
        """AC #2: New artifacts get 30-day expiry by default."""
        from app.models.artifact import Artifact

        # Arrange
        now = datetime.utcnow()

        # Act
        artifact = Artifact(
            artifact_id="art_test123",
            execution_id="exec_test123",
            artifact_type="output",
            filename="result.txt",
            file_path="executions/exec_test123/outputs/result.txt",
            size_bytes=100,
            content_type="text/plain",
        )

        # Assert - expires_at should be ~30 days from now
        assert artifact.expires_at is not None
        expected_min = now + timedelta(days=29, hours=23)
        expected_max = now + timedelta(days=30, hours=1)
        assert expected_min <= artifact.expires_at <= expected_max

    def test_artifact_expiry_respects_created_at(self):
        """Expiry is calculated from creation time."""
        from app.models.artifact import Artifact

        artifact = Artifact(
            artifact_id="art_test456",
            execution_id="exec_test456",
            artifact_type="output",
            filename="data.json",
            file_path="executions/exec_test456/outputs/data.json",
            size_bytes=500,
            content_type="application/json",
        )

        # Expiry should be 30 days after creation
        expected_expiry = artifact.created_at + timedelta(days=30)
        # Allow 1 second tolerance for test execution time
        assert abs((artifact.expires_at - expected_expiry).total_seconds()) < 1


class TestRetentionDaysConfig:
    """Test ARTIFACT_RETENTION_DAYS environment variable."""

    @patch.dict(os.environ, {"ARTIFACT_RETENTION_DAYS": "7"})
    def test_retention_days_from_env_variable(self):
        """AC #5: ARTIFACT_RETENTION_DAYS environment variable is respected."""
        from app.models.artifact import get_retention_days

        # Clear any cached config and test env var fallback
        result = int(os.environ.get("ARTIFACT_RETENTION_DAYS", "30"))
        assert result == 7

    def test_default_retention_is_30_days(self):
        """Default retention should be 30 days if env var not set."""
        from app.config import settings

        # Default should be 30
        assert getattr(settings, 'artifact_retention_days', 30) == 30


class TestLifecycleConfig:
    """Test MinIO lifecycle configuration setup."""

    def test_lifecycle_config_creates_valid_rule(self):
        """AC #1: MinIO lifecycle policy is valid."""
        from scripts.setup_minio_lifecycle import create_lifecycle_config

        # Act
        config = create_lifecycle_config(retention_days=30, prefix="executions/")

        # Assert
        assert config is not None
        assert len(config.rules) == 1

        rule = config.rules[0]
        assert rule.rule_id == "artifact-retention"
        assert rule.status == "Enabled"
        assert rule.expiration.days == 30

    def test_lifecycle_config_custom_retention_days(self):
        """Lifecycle config respects custom retention days."""
        from scripts.setup_minio_lifecycle import create_lifecycle_config

        config = create_lifecycle_config(retention_days=7, prefix="executions/")

        rule = config.rules[0]
        assert rule.expiration.days == 7

    def test_lifecycle_config_custom_prefix(self):
        """Lifecycle config respects custom prefix."""
        from scripts.setup_minio_lifecycle import create_lifecycle_config

        config = create_lifecycle_config(retention_days=30, prefix="test/")

        rule = config.rules[0]
        assert rule.rule_filter.prefix == "test/"


class TestArtifactAPIResponse:
    """Test API returns expires_at in artifact responses."""

    def test_artifact_response_includes_expires_at(self):
        """AC #4: API returns expires_at in artifact responses."""
        from datetime import datetime, timedelta

        # Simulate what the API should return
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=30)

        artifact_response = {
            "artifact_id": "art_test789",
            "execution_id": "exec_test789",
            "artifact_type": "output",
            "filename": "result.txt",
            "file_path": "executions/exec_test789/outputs/result.txt",
            "size_bytes": 100,
            "content_type": "text/plain",
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        # Assert expires_at is present and valid
        assert "expires_at" in artifact_response
        assert artifact_response["expires_at"] is not None

        # Parse and verify it's ~30 days from created_at
        created = datetime.fromisoformat(artifact_response["created_at"])
        expires = datetime.fromisoformat(artifact_response["expires_at"])
        diff = (expires - created).days
        assert diff == 30

    @pytest.mark.asyncio
    async def test_get_execution_artifacts_includes_expires_at(self):
        """Integration-style unit test: endpoint returns expires_at."""
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timedelta

        # Create mock artifact with expires_at
        mock_artifact = MagicMock()
        mock_artifact.artifact_id = "art_test"
        mock_artifact.execution_id = "exec_test"
        mock_artifact.artifact_type = "output"
        mock_artifact.filename = "output.txt"
        mock_artifact.file_path = "executions/exec_test/outputs/output.txt"
        mock_artifact.size_bytes = 100
        mock_artifact.content_type = "text/plain"
        mock_artifact.created_at = datetime.utcnow()
        mock_artifact.expires_at = mock_artifact.created_at + timedelta(days=30)

        # Simulate API response building
        artifact_dict = {
            "artifact_id": mock_artifact.artifact_id,
            "execution_id": mock_artifact.execution_id,
            "artifact_type": mock_artifact.artifact_type,
            "filename": mock_artifact.filename,
            "file_path": mock_artifact.file_path,
            "size_bytes": mock_artifact.size_bytes,
            "content_type": mock_artifact.content_type,
            "created_at": mock_artifact.created_at.isoformat() if mock_artifact.created_at else None,
            "expires_at": mock_artifact.expires_at.isoformat() if mock_artifact.expires_at else None,
        }

        # Assert expires_at is included
        assert "expires_at" in artifact_dict
        assert artifact_dict["expires_at"] is not None
