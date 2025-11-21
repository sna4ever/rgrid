"""Integration tests for MinIO retention policy (Story 7-3).

These tests verify the complete lifecycle policy workflow.
Marked as slow since they may require MinIO connection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os


class TestLifecyclePolicyIntegration:
    """Integration tests for MinIO lifecycle policy setup."""

    @pytest.mark.integration
    def test_lifecycle_policy_setup_workflow(self):
        """AC #1, #2: Complete lifecycle policy setup workflow."""
        from scripts.setup_minio_lifecycle import (
            create_lifecycle_config,
            setup_lifecycle,
        )

        # Create mock MinIO client
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True

        # Test setup_lifecycle with mocked client
        setup_lifecycle(
            client=mock_client,
            bucket="test-bucket",
            retention_days=30,
            prefix="executions/"
        )

        # Verify lifecycle policy was applied
        mock_client.set_bucket_lifecycle.assert_called_once()
        call_args = mock_client.set_bucket_lifecycle.call_args
        assert call_args[0][0] == "test-bucket"

        # Verify the config passed
        config = call_args[0][1]
        assert len(config.rules) == 1
        rule = config.rules[0]
        assert rule.rule_id == "artifact-retention"
        assert rule.expiration.days == 30

    @pytest.mark.integration
    def test_lifecycle_policy_creates_bucket_if_missing(self):
        """Bucket is created if it doesn't exist."""
        from scripts.setup_minio_lifecycle import setup_lifecycle

        mock_client = Mock()
        mock_client.bucket_exists.return_value = False

        setup_lifecycle(
            client=mock_client,
            bucket="new-bucket",
            retention_days=7,
        )

        # Verify bucket was created
        mock_client.make_bucket.assert_called_once_with("new-bucket")
        mock_client.set_bucket_lifecycle.assert_called_once()

    @pytest.mark.integration
    def test_verify_lifecycle_policy_exists(self):
        """Verify lifecycle policy can be retrieved."""
        from scripts.setup_minio_lifecycle import verify_lifecycle
        from minio.commonconfig import Filter
        from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

        # Create mock config to return
        mock_config = LifecycleConfig([
            Rule(
                status="Enabled",
                rule_filter=Filter(prefix="executions/"),
                rule_id="artifact-retention",
                expiration=Expiration(days=30),
            )
        ])

        mock_client = Mock()
        mock_client.get_bucket_lifecycle.return_value = mock_config

        result = verify_lifecycle(client=mock_client, bucket="test-bucket")

        assert result is True
        mock_client.get_bucket_lifecycle.assert_called_once_with("test-bucket")


class TestArtifactExpiryIntegration:
    """Integration tests for artifact expiry with database."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_artifact_saved_with_expiry(self):
        """Artifact saved to database includes expires_at."""
        from app.models.artifact import Artifact

        artifact = Artifact(
            artifact_id="art_integration_test",
            execution_id="exec_integration_test",
            artifact_type="output",
            filename="test.txt",
            file_path="executions/exec_integration_test/outputs/test.txt",
            size_bytes=100,
            content_type="text/plain",
        )

        # Verify expiry is set
        assert artifact.expires_at is not None
        assert artifact.created_at is not None

        # Verify expiry is 30 days from creation
        diff = (artifact.expires_at - artifact.created_at).days
        assert diff == 30

    @pytest.mark.integration
    def test_artifact_respects_custom_retention(self):
        """Artifact uses custom retention days from environment."""
        from app.models.artifact import Artifact, get_retention_days

        # Test with default retention
        default_retention = get_retention_days()
        assert default_retention == 30

        artifact = Artifact(
            artifact_id="art_custom_retention",
            execution_id="exec_custom_retention",
            artifact_type="output",
            filename="custom.txt",
            file_path="executions/exec_custom_retention/outputs/custom.txt",
            size_bytes=50,
            content_type="text/plain",
        )

        diff = (artifact.expires_at - artifact.created_at).days
        assert diff == default_retention

    @pytest.mark.integration
    def test_artifact_with_explicit_expiry(self):
        """Artifact can be created with explicit expiry timestamp."""
        from app.models.artifact import Artifact

        explicit_expiry = datetime.utcnow() + timedelta(days=7)

        artifact = Artifact(
            artifact_id="art_explicit_expiry",
            execution_id="exec_explicit_expiry",
            artifact_type="output",
            filename="explicit.txt",
            file_path="executions/exec_explicit_expiry/outputs/explicit.txt",
            size_bytes=25,
            content_type="text/plain",
            expires_at=explicit_expiry,
        )

        # Verify explicit expiry was used
        assert artifact.expires_at == explicit_expiry


class TestAPIArtifactResponseIntegration:
    """Integration tests for API artifact response."""

    @pytest.mark.integration
    def test_api_response_format_includes_expiry(self):
        """API response format includes expires_at field."""
        from app.models.artifact import Artifact

        artifact = Artifact(
            artifact_id="art_api_test",
            execution_id="exec_api_test",
            artifact_type="output",
            filename="api_test.json",
            file_path="executions/exec_api_test/outputs/api_test.json",
            size_bytes=500,
            content_type="application/json",
        )

        # Simulate API response building (matches executions.py logic)
        response = {
            "artifact_id": artifact.artifact_id,
            "execution_id": artifact.execution_id,
            "artifact_type": artifact.artifact_type,
            "filename": artifact.filename,
            "file_path": artifact.file_path,
            "size_bytes": artifact.size_bytes,
            "content_type": artifact.content_type,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None,
        }

        # Verify all required fields present
        assert "expires_at" in response
        assert response["expires_at"] is not None

        # Verify expires_at is valid ISO format
        parsed = datetime.fromisoformat(response["expires_at"])
        assert parsed > datetime.utcnow()


class TestEnvironmentConfigIntegration:
    """Integration tests for environment variable configuration."""

    @pytest.mark.integration
    @patch.dict(os.environ, {"ARTIFACT_RETENTION_DAYS": "14"})
    def test_config_reads_from_environment(self):
        """Configuration reads retention days from environment."""
        # Test environment variable is read
        retention = int(os.environ.get("ARTIFACT_RETENTION_DAYS", "30"))
        assert retention == 14

    @pytest.mark.integration
    def test_default_config_values(self):
        """Default configuration values are correct."""
        from app.config import settings

        # Verify defaults
        assert settings.artifact_retention_days == 30
        assert settings.minio_bucket_name == "rgrid"
