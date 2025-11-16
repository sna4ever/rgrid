"""Unit tests for Hetzner API client (Tier 4 - Story 4-1)."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from orchestrator.hetzner_client import HetznerClient, HETZNER_API_BASE


class TestHetznerClient:
    """Test Hetzner Cloud API client."""

    def test_client_initialization(self):
        """Client should initialize with API token."""
        client = HetznerClient("test_token_123")
        assert client.api_token == "test_token_123"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_token_123"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_server_success(self, mock_client_class):
        """Creating server should call Hetzner API and return response."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "server": {
                "id": 12345,
                "name": "rgrid-worker-abc",
                "status": "initializing"
            }
        }

        # Mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        result = await client.create_server(
            name="rgrid-worker-abc",
            ssh_key_id=123,
            user_data="#cloud-config\n...",
            labels={"project": "rgrid"}
        )

        # Assert
        assert result["server"]["id"] == 12345
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert HETZNER_API_BASE in call_args[0][0]

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_server_failure(self, mock_client_class):
        """Creating server should raise exception on API error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act & Assert
        client = HetznerClient("test_token")
        with pytest.raises(Exception, match="Invalid request"):
            await client.create_server(
                name="test",
                ssh_key_id=123,
                user_data="",
            )

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_delete_server_success(self, mock_client_class):
        """Deleting server should return True on success."""
        mock_response = Mock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        result = await client.delete_server(12345)

        # Assert
        assert result is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_server_found(self, mock_client_class):
        """Getting server should return server details if found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "server": {
                "id": 12345,
                "name": "rgrid-worker-abc"
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        result = await client.get_server(12345)

        # Assert
        assert result is not None
        assert result["id"] == 12345

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_server_not_found(self, mock_client_class):
        """Getting server should return None if not found."""
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        result = await client.get_server(99999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_list_servers(self, mock_client_class):
        """Listing servers should return array of servers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "servers": [
                {"id": 1, "name": "server1"},
                {"id": 2, "name": "server2"},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        result = await client.list_servers()

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_list_servers_with_label_filter(self, mock_client_class):
        """Listing servers with labels should pass label selector."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"servers": []}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        client = HetznerClient("test_token")
        await client.list_servers(labels={"project": "rgrid", "role": "worker"})

        # Assert
        call_args = mock_client.get.call_args
        params = call_args[1].get("params", {})
        assert "label_selector" in params
        assert "project=rgrid" in params["label_selector"]
