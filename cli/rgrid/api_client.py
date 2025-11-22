"""API client for communicating with RGrid backend."""

from typing import Optional, Any
import httpx
from rgrid.config import config
from rgrid.network_retry import create_api_wrapper


class APIClient:
    """Client for RGrid API.

    All API methods automatically retry on transient network failures
    (connection errors, timeouts, 502/503/504 responses) with exponential backoff.
    On persistent failures, a NetworkError is raised with a user-friendly message.

    Retry behavior (Story 10-5):
    - Displays "Connection lost. Retrying... (attempt 2/5)" during retries
    - Uses exponential backoff: 1s, 2s, 4s, 8s, 16s
    - On persistent failure: "Network error. Check connection and retry."
    """

    def __init__(self, enable_retry: bool = True) -> None:
        """Initialize API client.

        Args:
            enable_retry: If True (default), wrap API calls with retry logic.
                         Set to False for testing or when retry is not desired.
        """
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
        self._enable_retry = enable_retry

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request with optional retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            **kwargs: Arguments passed to httpx.Client.request()

        Returns:
            httpx.Response object
        """
        def do_request() -> httpx.Response:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response

        if self._enable_retry:
            wrapped = create_api_wrapper(do_request)
            return wrapped()
        else:
            return do_request()

    def create_execution(
        self,
        script_content: str,
        runtime: str = "python:3.11",
        args: Optional[list[str]] = None,
        env_vars: Optional[dict[str, str]] = None,
        input_files: Optional[list[str]] = None,
        batch_id: Optional[str] = None,
        requirements_content: Optional[str] = None,
        user_metadata: Optional[dict[str, str]] = None,
        cached_input_refs: Optional[dict[str, str]] = None,
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
            user_metadata: Optional user metadata tags (Story 10.8)
            cached_input_refs: Optional cached input file references (Story 6-4)

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

        # Add user_metadata if provided (Story 10.8)
        if user_metadata:
            payload["user_metadata"] = user_metadata

        # Add cached_input_refs if provided (Story 6-4)
        if cached_input_refs:
            payload["cached_input_refs"] = cached_input_refs

        response = self._request("POST", "/api/v1/executions", json=payload)
        return response.json()

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get execution status."""
        response = self._request("GET", f"/api/v1/executions/{execution_id}")
        return response.json()

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """
        Get execution statuses for all jobs in a batch.

        Args:
            batch_id: Batch ID to query

        Returns:
            Dictionary with list of execution statuses
        """
        response = self._request("GET", f"/api/v1/batches/{batch_id}/status")
        return response.json()

    def get_batch_executions(self, batch_id: str) -> list[dict[str, Any]]:
        """
        Get all executions in a batch with full metadata (Story 5-4).

        Args:
            batch_id: Batch ID to query

        Returns:
            List of execution dictionaries with batch_metadata including input_file
        """
        response = self._request("GET", f"/api/v1/batches/{batch_id}/executions")
        return response.json()

    def get_artifacts(self, execution_id: str) -> list[dict[str, Any]]:
        """
        Get artifacts for an execution (Story 7-5).

        Args:
            execution_id: Execution ID

        Returns:
            List of artifact dictionaries
        """
        response = self._request("GET", f"/api/v1/executions/{execution_id}/artifacts")
        return response.json()

    def download_artifact(self, artifact: dict[str, Any], target_path: str) -> None:
        """
        Download an artifact to local filesystem (Story 5-4).

        Args:
            artifact: Artifact dictionary with file_key
            target_path: Local path to save artifact
        """
        # TODO: Implement artifact download
        # For now, create empty file as placeholder
        import os
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w') as f:
            f.write("")

    def get_artifact_download_url(self, s3_key: str) -> str:
        """
        Get presigned download URL for an artifact (Story 7-5).

        Args:
            s3_key: S3 object key

        Returns:
            Presigned download URL
        """
        response = self._request(
            "POST",
            "/api/v1/artifacts/download-url",
            json={"s3_key": s3_key}
        )
        return response.json().get("download_url", "")

    def get_cost(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get cost breakdown by date range (Story 9-3).

        Args:
            since: Start date (YYYY-MM-DD). Default: 7 days ago
            until: End date (YYYY-MM-DD). Default: today

        Returns:
            CostResponse dictionary with daily breakdown and totals
        """
        params = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        response = self._request("GET", "/api/v1/cost", params=params)
        return response.json()

    def get_estimate(
        self,
        runtime: str = "python:3.11",
        files: int = 1,
    ) -> dict[str, Any]:
        """
        Get cost estimate for batch execution (Story 9-4).

        Args:
            runtime: Runtime to estimate for (e.g., "python:3.11")
            files: Number of files in batch

        Returns:
            EstimateResponse dictionary with cost breakdown and assumptions
        """
        params = {
            "runtime": runtime,
            "files": files,
        }

        response = self._request("GET", "/api/v1/estimate", params=params)
        return response.json()

    def retry_execution(self, execution_id: str) -> dict[str, Any]:
        """
        Retry an execution with the same parameters (Story 10-6).

        Creates a new execution using the script, runtime, args, env vars,
        and input files from the original execution.

        Args:
            execution_id: Original execution ID to retry

        Returns:
            New execution response with new execution_id
        """
        response = self._request("POST", f"/api/v1/executions/{execution_id}/retry")
        return response.json()

    def lookup_input_cache(self, input_hash: str) -> dict[str, Any]:
        """
        Look up cached input file references by hash (Story 6-4).

        Args:
            input_hash: SHA256 hash of combined input files (64 hex chars)

        Returns:
            Dictionary with cache_hit (bool) and file_references (dict) if hit
        """
        response = self._request("GET", f"/api/v1/input-cache/{input_hash}")
        return response.json()

    def store_input_cache(
        self,
        input_hash: str,
        file_references: dict[str, str],
    ) -> dict[str, Any]:
        """
        Store input cache entry after file upload (Story 6-4).

        Args:
            input_hash: SHA256 hash of combined input files (64 hex chars)
            file_references: Dict mapping filenames to MinIO object keys

        Returns:
            Dictionary with stored=True on success
        """
        payload = {
            "input_hash": input_hash,
            "file_references": file_references,
        }
        response = self._request("POST", "/api/v1/input-cache", json=payload)
        return response.json()

    def list_executions(
        self,
        metadata_filter: Optional[dict[str, str]] = None,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        List executions with optional filtering (Story 10.8).

        Args:
            metadata_filter: Filter by user_metadata tags (key=value pairs)
            limit: Maximum number of executions to return (default 50)
            status: Optional status filter (queued, running, completed, failed)

        Returns:
            List of execution summaries
        """
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if metadata_filter:
            # Pass metadata as query params: metadata[key]=value
            for key, value in metadata_filter.items():
                params[f"metadata[{key}]"] = value

        response = self._request("GET", "/api/v1/executions", params=params)
        return response.json()

    def get_spending_limit(self) -> dict[str, Any]:
        """
        Get current spending limit and usage status (Story 9-5).

        Returns:
            SpendingLimitResponse dictionary with limit and usage information
        """
        response = self._request("GET", "/api/v1/cost/limit")
        return response.json()

    def set_spending_limit(self, monthly_limit_euros: float) -> dict[str, Any]:
        """
        Set a monthly spending limit (Story 9-5).

        Args:
            monthly_limit_euros: Monthly limit in euros (e.g., 50.0 for €50/month)

        Returns:
            LimitSetResponse dictionary confirming the limit was set
        """
        response = self._request(
            "PUT",
            "/api/v1/cost/limit",
            json={"monthly_limit_euros": monthly_limit_euros}
        )
        return response.json()

    def remove_spending_limit(self) -> dict[str, Any]:
        """
        Remove the spending limit (Story 9-5).

        Returns:
            Success message
        """
        response = self._request("DELETE", "/api/v1/cost/limit")
        return response.json()

    def close(self) -> None:
        """Close client connection."""
        self.client.close()


def get_client() -> APIClient:
    """Get API client instance."""
    return APIClient()
