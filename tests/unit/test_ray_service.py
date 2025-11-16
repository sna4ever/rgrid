"""Unit tests for Ray service (Tier 4 - Story 3-3)."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestRayService:
    """Test Ray service functionality."""

    @patch('app.ray_service.ray')
    def test_ray_service_initialization_when_disabled(self, mock_ray):
        """When Ray is disabled in config, initialization should return False."""
        with patch('app.ray_service.settings') as mock_settings:
            mock_settings.ray_enabled = False
            mock_settings.ray_head_address = "ray://localhost:10001"

            from app.ray_service import RayService

            # Create service with Ray disabled
            service = RayService()

            # Act
            result = service.initialize()

            # Assert
            assert result is False
            assert service.is_initialized() is False
            mock_ray.init.assert_not_called()

    @patch('app.ray_service.ray')
    def test_ray_service_initialization_success(self, mock_ray):
        """When Ray init succeeds, is_initialized should return True."""
        with patch('app.ray_service.settings') as mock_settings:
            mock_settings.ray_enabled = True
            mock_settings.ray_head_address = "ray://localhost:10001"

            from app.ray_service import RayService

            # Arrange
            mock_ray.init.return_value = None
            service = RayService()

            # Act
            result = service.initialize()

            # Assert
            assert result is True
            assert service.is_initialized() is True
            mock_ray.init.assert_called_once()

    @patch('app.ray_service.ray')
    def test_ray_service_initialization_failure(self, mock_ray):
        """When Ray init fails, should return False."""
        with patch('app.ray_service.settings') as mock_settings:
            mock_settings.ray_enabled = True
            mock_settings.ray_head_address = "ray://localhost:10001"

            from app.ray_service import RayService

            # Arrange
            mock_ray.init.side_effect = Exception("Connection failed")
            service = RayService()

            # Act
            result = service.initialize()

            # Assert
            assert result is False
            assert service.is_initialized() is False

    @patch('app.ray_service.ray')
    def test_submit_execution_task_when_not_initialized(self, mock_ray):
        """When Ray is not initialized, submit should return None."""
        from app.ray_service import RayService

        # Arrange
        service = RayService()
        service._initialized = False

        # Act
        result = service.submit_execution_task("exec_123", "postgresql://...")

        # Assert
        assert result is None

    @patch('app.ray_service.ray')
    def test_submit_execution_task_success(self, mock_ray):
        """When Ray task submission succeeds, should return task ID."""
        from app.ray_service import RayService

        # Arrange
        mock_task_ref = Mock()
        mock_task_ref.hex.return_value = "abc123def456"

        # Mock the execute_script_task module import
        mock_execute_task = Mock()
        mock_execute_task.remote.return_value = mock_task_ref

        service = RayService()
        service._initialized = True

        # Patch the dynamic import inside submit_execution_task
        import sys
        mock_runner_module = Mock()
        mock_runner_module.ray_tasks = Mock()
        mock_runner_module.ray_tasks.execute_script_task = mock_execute_task
        sys.modules['runner'] = mock_runner_module
        sys.modules['runner.ray_tasks'] = mock_runner_module.ray_tasks

        try:
            # Act
            result = service.submit_execution_task("exec_123", "postgresql://...")

            # Assert
            assert result == "abc123def456"
            mock_execute_task.remote.assert_called_once_with("exec_123", "postgresql://...")
        finally:
            # Clean up mocks
            if 'runner' in sys.modules:
                del sys.modules['runner']
            if 'runner.ray_tasks' in sys.modules:
                del sys.modules['runner.ray_tasks']

    @patch('app.ray_service.ray')
    def test_shutdown_when_initialized(self, mock_ray):
        """When shutting down initialized service, should call ray.shutdown()."""
        from app.ray_service import RayService

        # Arrange
        service = RayService()
        service._initialized = True

        # Act
        service.shutdown()

        # Assert
        mock_ray.shutdown.assert_called_once()
        assert service.is_initialized() is False

    @patch('app.ray_service.ray')
    def test_shutdown_when_not_initialized(self, mock_ray):
        """When shutting down non-initialized service, should not error."""
        from app.ray_service import RayService

        # Arrange
        service = RayService()
        service._initialized = False

        # Act - should not raise
        service.shutdown()

        # Assert
        assert service.is_initialized() is False
        mock_ray.shutdown.assert_not_called()


class TestRayServiceConfiguration:
    """Test Ray service configuration."""

    @patch('app.ray_service.settings')
    def test_ray_service_uses_correct_address_from_settings(self, mock_settings):
        """Ray service should use address from settings."""
        mock_settings.ray_enabled = True
        mock_settings.ray_head_address = "ray://test:12345"

        from app.ray_service import RayService

        # Arrange
        service = RayService()

        # Assert
        assert service._ray_address == "ray://test:12345"

    @patch('app.ray_service.settings')
    def test_ray_service_respects_enabled_flag(self, mock_settings):
        """Ray service should respect the enabled flag from settings."""
        mock_settings.ray_enabled = False
        mock_settings.ray_head_address = "ray://localhost:10001"

        from app.ray_service import RayService

        # Arrange
        service = RayService()

        # Assert
        assert service._ray_enabled is False
