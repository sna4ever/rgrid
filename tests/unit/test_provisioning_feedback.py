"""Unit tests for provisioning user feedback (Tier 4 - Story NEW-4)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from orchestrator.provisioner import WorkerProvisioner


class TestProvisioningFeedback:
    """Test provisioning user feedback and error handling."""

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_provision_with_eta_message(self, mock_hetzner_class):
        """Provisioning should show ETA message on first attempt."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(return_value={
            "server": {
                "id": 12345,
                "public_net": {"ipv4": {"ip": "192.168.1.1"}}
            }
        })
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

            async with async_session_maker() as session:
                # Mock table creation
                with patch.object(session, 'add'):
                    await provisioner.provision_worker(session)

            # Assert - Check that ETA message was logged
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("ETA: ~90 seconds" in str(call) for call in info_calls), \
                f"Expected ETA message in logs, got: {info_calls}"

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_provision_retry_with_attempt_number(self, mock_hetzner_class):
        """Retry attempts should show attempt number."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(side_effect=Exception("Temporary error"))
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
                engine = create_async_engine("sqlite+aiosqlite:///:memory:")
                async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

                async with async_session_maker() as session:
                    result = await provisioner.provision_worker(session)

                # Assert
                assert result is None  # Should fail after retries
                # Check retry messages
                info_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("attempt 2/3" in str(call) for call in info_calls)
                assert any("attempt 3/3" in str(call) for call in info_calls)

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_quota_exceeded_error_message(self, mock_hetzner_class):
        """Quota exceeded should show user-friendly message."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(
            side_effect=Exception("Server limit quota exceeded")
        )
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

            async with async_session_maker() as session:
                result = await provisioner.provision_worker(session)

            # Assert
            assert result is None
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any(
                "Worker limit reached" in str(call) and
                "Upgrade Hetzner account" in str(call)
                for call in error_calls
            )

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_network_error_message(self, mock_hetzner_class):
        """Network errors should show user-friendly message."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(
            side_effect=Exception("Network connection timeout")
        )
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
                engine = create_async_engine("sqlite+aiosqlite:///:memory:")
                async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

                async with async_session_maker() as session:
                    result = await provisioner.provision_worker(session)

            # Assert
            assert result is None
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any(
                "Cannot reach cloud provider" in str(call) and
                "Check network connection" in str(call)
                for call in error_calls
            )

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_authentication_error_message(self, mock_hetzner_class):
        """Authentication errors should show user-friendly message."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(
            side_effect=Exception("Unauthorized: Invalid API token")
        )
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
                engine = create_async_engine("sqlite+aiosqlite:///:memory:")
                async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

                async with async_session_maker() as session:
                    result = await provisioner.provision_worker(session)

            # Assert
            assert result is None
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any(
                "authentication failed" in str(call) and
                "HETZNER_API_TOKEN" in str(call)
                for call in error_calls
            )

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_generic_error_message(self, mock_hetzner_class):
        """Generic errors should show cloud provider error message."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(
            side_effect=Exception("Something went wrong")
        )
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
                engine = create_async_engine("sqlite+aiosqlite:///:memory:")
                async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

                async with async_session_maker() as session:
                    result = await provisioner.provision_worker(session)

            # Assert
            assert result is None
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any(
                "Cloud provider error" in str(call)
                for call in error_calls
            )

    @pytest.mark.asyncio
    @patch('orchestrator.provisioner.HetznerClient')
    async def test_successful_provision_shows_ready_time(self, mock_hetzner_class):
        """Successful provisioning should show ready time estimate."""
        # Arrange
        mock_hetzner = Mock()
        mock_hetzner.create_server = AsyncMock(return_value={
            "server": {
                "id": 12345,
                "public_net": {"ipv4": {"ip": "192.168.1.1"}}
            }
        })
        mock_hetzner_class.return_value = mock_hetzner

        provisioner = WorkerProvisioner(
            "postgresql+asyncpg://test",
            "test_token",
            "/tmp/test_key"
        )
        provisioner._ssh_key_id = 1

        # Act
        with patch('orchestrator.provisioner.logger') as mock_logger:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

            async with async_session_maker() as session:
                with patch.object(session, 'add'):
                    result = await provisioner.provision_worker(session)

            # Assert
            assert result is not None
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("~60 seconds" in str(call) for call in info_calls)
