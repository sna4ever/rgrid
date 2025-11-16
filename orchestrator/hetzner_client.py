"""Hetzner Cloud API client for worker provisioning (Tier 4 - Story 4-1)."""

import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)

# Hetzner Cloud API base URL
HETZNER_API_BASE = "https://api.hetzner.cloud/v1"

# Server types and configurations
SERVER_TYPE = "cx22"  # 2 vCPU, 4GB RAM
LOCATION = "nbg1"  # Nuremberg
IMAGE = "ubuntu-22.04"


class HetznerClient:
    """Hetzner Cloud API client."""

    def __init__(self, api_token: str):
        """
        Initialize Hetzner client.

        Args:
            api_token: Hetzner Cloud API token
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def create_server(
        self,
        name: str,
        ssh_key_id: int,
        user_data: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new server.

        Args:
            name: Server name
            ssh_key_id: SSH key ID
            user_data: Cloud-init user data
            labels: Optional server labels

        Returns:
            Server creation response

        Raises:
            Exception: If server creation fails
        """
        url = f"{HETZNER_API_BASE}/servers"

        payload = {
            "name": name,
            "server_type": SERVER_TYPE,
            "location": LOCATION,
            "image": IMAGE,
            "ssh_keys": [ssh_key_id],
            "user_data": user_data,
            "labels": labels or {},
            "automount": False,
            "start_after_create": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)

            if response.status_code == 201:
                data = response.json()
                logger.info(f"Server {name} created successfully (ID: {data['server']['id']})")
                return data
            else:
                error = response.json()
                logger.error(f"Failed to create server {name}: {error}")
                raise Exception(f"Hetzner API error: {error.get('error', {}).get('message', 'Unknown error')}")

    async def delete_server(self, server_id: int) -> bool:
        """
        Delete a server.

        Args:
            server_id: Server ID

        Returns:
            True if successful

        Raises:
            Exception: If deletion fails
        """
        url = f"{HETZNER_API_BASE}/servers/{server_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self.headers)

            if response.status_code in (200, 204):
                logger.info(f"Server {server_id} deleted successfully")
                return True
            else:
                error = response.json()
                logger.error(f"Failed to delete server {server_id}: {error}")
                raise Exception(f"Hetzner API error: {error.get('error', {}).get('message', 'Unknown error')}")

    async def get_server(self, server_id: int) -> Optional[Dict[str, Any]]:
        """
        Get server details.

        Args:
            server_id: Server ID

        Returns:
            Server details or None if not found
        """
        url = f"{HETZNER_API_BASE}/servers/{server_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()["server"]
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Failed to get server {server_id}: {response.text}")
                return None

    async def list_servers(self, labels: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        List all servers, optionally filtered by labels.

        Args:
            labels: Optional label filter

        Returns:
            List of servers
        """
        url = f"{HETZNER_API_BASE}/servers"

        params = {}
        if labels:
            # Format: label_selector=key1=value1,key2=value2
            label_selector = ",".join(f"{k}={v}" for k, v in labels.items())
            params["label_selector"] = label_selector

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return response.json()["servers"]
            else:
                logger.error(f"Failed to list servers: {response.text}")
                return []

    async def get_ssh_keys(self) -> List[Dict[str, Any]]:
        """
        Get all SSH keys.

        Returns:
            List of SSH keys
        """
        url = f"{HETZNER_API_BASE}/ssh_keys"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()["ssh_keys"]
            else:
                logger.error(f"Failed to get SSH keys: {response.text}")
                return []

    async def create_ssh_key(self, name: str, public_key: str) -> Dict[str, Any]:
        """
        Create SSH key.

        Args:
            name: Key name
            public_key: Public key content

        Returns:
            SSH key details
        """
        url = f"{HETZNER_API_BASE}/ssh_keys"

        payload = {
            "name": name,
            "public_key": public_key,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)

            if response.status_code == 201:
                return response.json()["ssh_key"]
            else:
                error = response.json()
                raise Exception(f"Failed to create SSH key: {error}")

    async def get_server_metrics(self, server_id: int) -> Optional[Dict[str, Any]]:
        """
        Get server metrics.

        Args:
            server_id: Server ID

        Returns:
            Server metrics or None
        """
        url = f"{HETZNER_API_BASE}/servers/{server_id}/metrics"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()["metrics"]
            else:
                return None
