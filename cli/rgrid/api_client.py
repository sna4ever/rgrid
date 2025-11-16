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
        input_files: Optional[list[str]] = None,
        batch_id: Optional[str] = None,
        requirements_content: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new execution.

        Args:
            script_content: Python script source code
            runtime: Runtime environment
            args: Script arguments
            env_vars: Environment variables
            input_files: List of input file names (Tier 4 - Story 2-5)
            batch_id: Optional batch ID for grouping executions (Tier 5 - Story 5-3)
            requirements_content: Optional requirements.txt content for dependency caching (Story 6-2)

        Returns:
            Execution response (includes upload_urls if input_files provided)
        """
        payload = {
            "script_content": script_content,
            "runtime": runtime,
            "args": args or [],
            "env_vars": env_vars or {},
            "input_files": input_files or [],
        }

        # Add batch_id if provided
        if batch_id:
            payload["batch_id"] = batch_id

        # Add requirements_content if provided (Story 6-2)
        if requirements_content:
            payload["requirements_content"] = requirements_content

        response = self.client.post(
            "/api/v1/executions",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get execution status."""
        response = self.client.get(f"/api/v1/executions/{execution_id}")
        response.raise_for_status()
        return response.json()

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """
        Get execution statuses for all jobs in a batch.

        Args:
            batch_id: Batch ID to query

        Returns:
            Dictionary with list of execution statuses
        """
        response = self.client.get(f"/api/v1/batches/{batch_id}/status")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close client connection."""
        self.client.close()


def get_client() -> APIClient:
    """Get API client instance."""
    return APIClient()
