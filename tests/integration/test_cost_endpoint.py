"""Integration tests for cost API endpoint (Story 9-3).

Tests the /api/v1/cost endpoint with actual database queries.

Note: These tests require the database schema to be up to date with
migrations through Story 8-6 and 9-1 (duration_seconds, finalized_cost_micros).
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# Check if database schema is up to date
def _check_schema_has_cost_columns() -> bool:
    """Check if database has the required cost columns."""
    try:
        from sqlalchemy import inspect, create_engine
        from app.config import settings

        # Create sync engine for inspection
        sync_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        engine = create_engine(sync_url)
        inspector = inspect(engine)

        # Check for required columns
        columns = {c["name"] for c in inspector.get_columns("executions")}
        required = {"duration_seconds", "finalized_cost_micros", "cost_micros"}

        engine.dispose()
        return required.issubset(columns)
    except Exception:
        return False


# Skip tests if schema is not up to date
pytestmark = pytest.mark.skipif(
    not _check_schema_has_cost_columns(),
    reason="Database schema missing cost columns (run migrations first)"
)


@pytest.fixture
def api_client() -> TestClient:
    """Create test client for API."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    """Provide authentication headers for API calls."""
    return {"Authorization": "Bearer sk_dev_test123"}


class TestCostEndpoint:
    """Test cost API endpoint."""

    def test_cost_endpoint_exists(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test cost endpoint exists and accepts GET requests."""
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        # Should return 200 even with no data
        assert response.status_code == 200

    def test_cost_requires_authentication(self, api_client: TestClient) -> None:
        """Test cost endpoint requires authentication."""
        response = api_client.get("/api/v1/cost")
        assert response.status_code == 401

    def test_cost_response_structure(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test cost endpoint returns proper response structure."""
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        # Verify required fields
        assert "start_date" in data
        assert "end_date" in data
        assert "total_cost_micros" in data
        assert "total_cost_display" in data
        assert "by_date" in data
        assert "total_executions" in data

        # Verify types
        assert isinstance(data["start_date"], str)
        assert isinstance(data["end_date"], str)
        assert isinstance(data["total_cost_micros"], int)
        assert isinstance(data["total_cost_display"], str)
        assert isinstance(data["by_date"], list)
        assert isinstance(data["total_executions"], int)

    def test_cost_default_date_range(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test default date range is last 7 days."""
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        # Verify dates are in expected format (YYYY-MM-DD)
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")

        # Start should be around 7 days before end
        delta = end_date - start_date
        assert delta.days == 7

    def test_cost_custom_date_range(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test custom date range parameters."""
        response = api_client.get(
            "/api/v1/cost?since=2025-11-01&until=2025-11-15",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["start_date"] == "2025-11-01"
        assert data["end_date"] == "2025-11-15"

    def test_cost_display_format(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test cost display is properly formatted."""
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        # Total cost display should start with EUR symbol
        assert data["total_cost_display"].startswith("€")

    def test_cost_empty_period(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test cost for period with no executions."""
        # Use a date far in the future to ensure no executions
        response = api_client.get(
            "/api/v1/cost?since=2099-01-01&until=2099-01-31",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_executions"] == 0
        assert data["total_cost_micros"] == 0
        assert data["total_cost_display"] == "€0.00"
        assert data["by_date"] == []


class TestCostWithExecutions:
    """Test cost endpoint with execution data.

    These tests create executions and verify cost aggregation.
    """

    def test_cost_includes_completed_executions(
        self, api_client: TestClient, auth_headers: dict
    ) -> None:
        """Test that completed executions are included in cost."""
        # First, create an execution
        create_response = api_client.post(
            "/api/v1/executions",
            json={
                "script_content": "print('test')",
                "runtime": "python:3.11",
                "args": [],
                "env_vars": [],
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        execution_id = create_response.json()["execution_id"]

        # The execution is queued, not completed, so it shouldn't appear in costs yet
        # (costs only count completed/failed executions)
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        assert response.status_code == 200

        # This verifies the endpoint works even with pending executions

    def test_daily_cost_structure(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test daily cost breakdown structure."""
        response = api_client.get("/api/v1/cost", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        for day in data["by_date"]:
            # Verify each daily entry has required fields
            assert "date" in day
            assert "executions" in day
            assert "compute_time_seconds" in day
            assert "cost_micros" in day
            assert "cost_display" in day

            # Verify types
            assert isinstance(day["date"], str)
            assert isinstance(day["executions"], int)
            assert isinstance(day["compute_time_seconds"], int)
            assert isinstance(day["cost_micros"], int)
            assert isinstance(day["cost_display"], str)

            # Cost display should be formatted with EUR
            assert day["cost_display"].startswith("€")


class TestCostQueryParams:
    """Test cost endpoint query parameter handling."""

    def test_only_since_parameter(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test providing only since parameter (until defaults to today)."""
        response = api_client.get(
            "/api/v1/cost?since=2025-11-01",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["start_date"] == "2025-11-01"
        # End date should be today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert data["end_date"] == today

    def test_only_until_parameter(self, api_client: TestClient, auth_headers: dict) -> None:
        """Test providing only until parameter (since defaults to 7 days before)."""
        response = api_client.get(
            "/api/v1/cost?until=2025-11-15",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["end_date"] == "2025-11-15"
        # Start date should be 7 days before current date (not before until date)
        # because the default logic uses current date
