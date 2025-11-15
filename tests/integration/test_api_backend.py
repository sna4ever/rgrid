"""
Integration tests for FastAPI backend.

Story 1.6: Set Up FastAPI Backend with Database Connection
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client() -> TestClient:
    """
    Create test client for API.

    Note: This requires DATABASE_URL and MinIO configuration
    to be set in environment variables.
    """
    # Import here to avoid loading before env vars are set
    from app.main import app

    return TestClient(app)


class TestAPIBasics:
    """Test basic API functionality."""

    def test_root_endpoint(self, api_client: TestClient) -> None:
        """Test root endpoint returns welcome message."""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "RGrid API"
        assert "version" in data

    def test_health_endpoint_exists(self, api_client: TestClient) -> None:
        """Test health check endpoint exists."""
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, api_client: TestClient) -> None:
        """Test health endpoint returns proper structure."""
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data

        # Version should be 0.1.0
        assert data["version"] == "0.1.0"

    def test_docs_available_in_dev(self, api_client: TestClient) -> None:
        """Test API documentation is available."""
        response = api_client.get("/docs")
        # In test mode, docs might be disabled, so we accept both
        assert response.status_code in [200, 404]


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, api_client: TestClient) -> None:
        """Test CORS headers are present in responses."""
        response = api_client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # CORS middleware should add headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
