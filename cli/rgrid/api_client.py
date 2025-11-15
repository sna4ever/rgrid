"""API client for communicating with RGrid backend."""

from typing import Optional, Any
import httpx
from rgrid.config import config


class APIClient:
    """Client for RGrid API."""

    def __init__(self) -> None:
        """Initialize API client."""
        creds = config.load_credentials()
        if not creds:
            raise RuntimeError(
                "No credentials found. Run 'rgrid init' first."
            )

        self.api_url = creds["api_url"]
        self.api_key = creds["api_key"]
        self.client = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    def create_execution(
        self,
        script_content: str,
        runtime: str = "python:3.11",
        args: Optional[list[str]] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Create a new execution.

        Args:
            script_content: Python script source code
            runtime: Runtime environment
            args: Script arguments
            env_vars: Environment variables

        Returns:
            Execution response
        """
        response = self.client.post(
            "/api/v1/executions",
            json={
                "script_content": script_content,
                "runtime": runtime,
                "args": args or [],
                "env_vars": env_vars or {},
            },
        )
        response.raise_for_status()
        return response.json()

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get execution status."""
        response = self.client.get(f"/api/v1/executions/{execution_id}")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close client connection."""
        self.client.close()


def get_client() -> APIClient:
    """Get API client instance."""
    return APIClient()
