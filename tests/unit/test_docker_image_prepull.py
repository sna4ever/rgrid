"""Unit tests for Docker image pre-pulling (Tier 4 - Story 4-4)."""

import pytest
from orchestrator.provisioner import WorkerProvisioner


class TestDockerImagePrePull:
    """Test Docker image pre-pulling optimization."""

    def test_cloud_init_includes_python_images(self):
        """Cloud-init should include python:3.11-slim image pull."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        assert "docker pull python:3.11-slim" in cloud_init
        assert "docker pull python:3.10-slim" in cloud_init
        assert "docker pull python:3.9-slim" in cloud_init

    def test_cloud_init_includes_node_images(self):
        """Cloud-init should include Node.js images."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        assert "docker pull node:20-slim" in cloud_init
        assert "docker pull node:18-slim" in cloud_init

    def test_cloud_init_pulls_in_background(self):
        """Docker pulls should run in background to not block worker startup."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert - Check for background execution syntax
        assert "docker pull python:3.11-slim &" in cloud_init
        assert "docker pull node:20-slim &" in cloud_init
        assert "wait" in cloud_init  # Wait for background jobs

    def test_cloud_init_has_prepull_comment(self):
        """Cloud-init should document the pre-pull optimization."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        assert "Pre-pulling common Docker images" in cloud_init or "pre-pull" in cloud_init.lower()
        assert "Story 4-4" in cloud_init  # Reference to story

    def test_cloud_init_prepull_before_ray_start(self):
        """Docker images should be pre-pulled before Ray worker starts."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert - Docker pull commands should appear before Ray start
        docker_pull_index = cloud_init.index("docker pull python:3.11-slim")
        ray_start_index = cloud_init.index("ray start")

        assert docker_pull_index < ray_start_index, "Docker pulls should happen before Ray starts"

    def test_prepull_includes_slim_variants(self):
        """Should use slim variants for smaller download size."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        assert "-slim" in cloud_init
        # Slim variants should be used for common images
        assert "python:3.11-slim" in cloud_init
        assert "node:20-slim" in cloud_init

    def test_cloud_init_format_is_valid_yaml(self):
        """Cloud-init should be valid YAML format."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        assert cloud_init.startswith("#cloud-config")
        assert "package_update:" in cloud_init
        assert "runcmd:" in cloud_init

    def test_custom_images_are_commented_out(self):
        """Custom images should be present but commented for future use."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-test123")

        # Assert
        # Custom images should be present as comments for documentation
        # (Users can uncomment when they build custom images)
        assert "# - docker pull" in cloud_init or "rgrid/" in cloud_init

    def test_worker_id_in_cloud_init(self):
        """Worker ID should be included in cloud-init."""
        # Arrange
        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test:test@localhost/rgrid",
            "test_token",
            "/tmp/test_key"
        )

        # Act
        cloud_init = provisioner._generate_cloud_init("worker-abc123")

        # Assert
        assert "worker-abc123" in cloud_init
        assert "WORKER_ID=worker-abc123" in cloud_init
