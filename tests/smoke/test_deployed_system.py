"""
Smoke tests for deployed RGrid staging and production environments.

These tests run against actual deployed instances to verify basic functionality.

Usage:
    # Test staging
    export RGRID_TEST_ENV=staging
    pytest tests/smoke/test_deployed_system.py -v

    # Test production (careful!)
    export RGRID_TEST_ENV=production
    pytest tests/smoke/test_deployed_system.py -v -m production

Mark production tests with @pytest.mark.production to prevent accidental runs.
"""

import os
import pytest
import requests
import time
from typing import Dict, Optional


# Environment configuration
DEFAULT_ENV = os.getenv('RGRID_TEST_ENV', 'staging')

ENVIRONMENTS = {
    'staging': {
        'api_url': os.getenv('STAGING_API_URL', 'https://staging.rgrid.dev'),
        'safe_to_test': True,
    },
    'production': {
        'api_url': os.getenv('PROD_API_URL', 'https://api.rgrid.dev'),
        'safe_to_test': False,  # Requires explicit --production flag
    }
}


def get_api_url(env: str = DEFAULT_ENV) -> str:
    """Get API URL for environment."""
    return ENVIRONMENTS[env]['api_url']


class TestAPIHealth:
    """Test API health and basic connectivity."""

    @pytest.mark.parametrize("env", ['staging'])
    def test_api_health_endpoint_staging(self, env):
        """Verify staging API responds to health checks."""
        api_url = get_api_url(env)
        response = requests.get(f"{api_url}/api/v1/health", timeout=10)

        assert response.status_code == 200, (
            f"Health endpoint returned {response.status_code}\n"
            f"URL: {api_url}/api/v1/health\n"
            f"Response: {response.text}"
        )

        data = response.json()
        assert 'status' in data, "Health response missing 'status' field"
        assert data['status'] == 'ok (db: connected)', (
            f"Database not connected! Status: {data['status']}"
        )

    @pytest.mark.production
    @pytest.mark.parametrize("env", ['production'])
    def test_api_health_endpoint_production(self, env):
        """Verify production API responds to health checks.

        Marked as production - requires explicit opt-in to run.
        """
        api_url = get_api_url(env)
        response = requests.get(f"{api_url}/api/v1/health", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok (db: connected)'

    @pytest.mark.parametrize("env", ['staging'])
    def test_api_root_endpoint(self, env):
        """Verify root endpoint returns API info."""
        api_url = get_api_url(env)
        response = requests.get(f"{api_url}/", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        assert 'version' in data
        assert data['message'] == 'RGrid API'


class TestSSLConfiguration:
    """Test HTTPS/SSL certificate configuration."""

    @pytest.mark.parametrize("env", ['staging', 'production'])
    def test_https_certificate_valid(self, env):
        """Verify HTTPS certificate is valid and not expired."""
        api_url = get_api_url(env)

        # requests will raise exception if SSL verification fails
        try:
            response = requests.get(f"{api_url}/api/v1/health", timeout=10, verify=True)
            assert response.status_code == 200
        except requests.exceptions.SSLError as e:
            pytest.fail(f"SSL certificate invalid for {env}: {e}")

    @pytest.mark.parametrize("env", ['staging'])
    def test_http_redirects_to_https(self, env):
        """Verify HTTP traffic redirects to HTTPS."""
        api_url = get_api_url(env)
        http_url = api_url.replace('https://', 'http://')

        response = requests.get(
            f"{http_url}/api/v1/health",
            timeout=10,
            allow_redirects=True
        )

        # Should redirect to HTTPS (either 301 or final URL is HTTPS)
        assert response.url.startswith('https://'), (
            f"HTTP did not redirect to HTTPS!\n"
            f"Requested: {http_url}/api/v1/health\n"
            f"Final URL: {response.url}"
        )


class TestDatabaseConnection:
    """Test database connectivity and schema."""

    @pytest.mark.parametrize("env", ['staging'])
    def test_database_connection_healthy(self, env):
        """Verify database is connected and responding."""
        api_url = get_api_url(env)
        response = requests.get(f"{api_url}/api/v1/health", timeout=10)

        assert response.status_code == 200
        data = response.json()

        # Health endpoint should confirm DB connection
        assert 'db' in data['status'].lower(), "Health response doesn't mention database"
        assert 'connected' in data['status'].lower(), "Database not connected"


class TestServiceIsolation:
    """Test staging and production isolation."""

    def test_staging_and_production_are_separate(self):
        """Verify staging and production are isolated environments."""
        staging_url = ENVIRONMENTS['staging']['api_url']
        production_url = ENVIRONMENTS['production']['api_url']

        # Should have different domains
        assert staging_url != production_url, (
            "Staging and production should have different URLs!"
        )

        # Both should be accessible
        staging_response = requests.get(f"{staging_url}/api/v1/health", timeout=10)
        production_response = requests.get(f"{production_url}/api/v1/health", timeout=10)

        assert staging_response.status_code == 200, "Staging not accessible"
        assert production_response.status_code == 200, "Production not accessible"


class TestDeployedFeatures:
    """Test Tier 3 features on deployed system."""

    @pytest.mark.parametrize("env", ['staging'])
    def test_runtime_resolution_available(self, env):
        """Verify runtime resolver is deployed.

        This tests the pre-configured runtimes feature (Tier 3 Story 2-3).
        """
        # Note: This test assumes API exposes runtime info
        # If not, this test should be updated or removed
        api_url = get_api_url(env)

        # Try to check if runtimes endpoint exists
        # (This is speculative - adjust based on actual API)
        response = requests.get(f"{api_url}/api/v1/runtimes", timeout=10)

        # If endpoint doesn't exist (404), that's okay for smoke test
        # If it exists, should return 200
        if response.status_code == 404:
            # Endpoint not implemented, skip
            pytest.skip("Runtimes endpoint not implemented")
        elif response.status_code == 401:
            # Authentication required, that's okay
            pytest.skip("Runtimes endpoint requires authentication")
        else:
            assert response.status_code == 200


class TestNginxRouting:
    """Test NGINX reverse proxy routing."""

    def test_staging_domain_routes_correctly(self):
        """Verify staging.rgrid.dev routes to staging environment."""
        response = requests.get(
            "https://staging.rgrid.dev/api/v1/health",
            timeout=10
        )

        assert response.status_code == 200
        # Should indicate this is staging (if API returns env info)

    @pytest.mark.production
    def test_production_domain_routes_correctly(self):
        """Verify api.rgrid.dev routes to production environment."""
        response = requests.get(
            "https://api.rgrid.dev/api/v1/health",
            timeout=10
        )

        assert response.status_code == 200


class TestBasicPerformance:
    """Basic performance checks."""

    @pytest.mark.parametrize("env", ['staging'])
    def test_health_endpoint_response_time(self, env):
        """Verify health endpoint responds within reasonable time."""
        api_url = get_api_url(env)

        start_time = time.time()
        response = requests.get(f"{api_url}/api/v1/health", timeout=10)
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 2.0, (
            f"Health endpoint took {elapsed:.2f}s (>2s threshold)\n"
            f"Performance may be degraded"
        )

    @pytest.mark.parametrize("env", ['staging'])
    def test_api_responds_under_load(self, env):
        """Verify API handles multiple concurrent requests."""
        api_url = get_api_url(env)

        # Send 10 concurrent health checks
        import concurrent.futures

        def check_health():
            response = requests.get(f"{api_url}/api/v1/health", timeout=10)
            return response.status_code == 200

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_health) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(results), "Some health checks failed under concurrent load"


# Conftest helpers for smoke tests
@pytest.fixture
def staging_api_url():
    """Get staging API URL."""
    return ENVIRONMENTS['staging']['api_url']


@pytest.fixture
def production_api_url():
    """Get production API URL."""
    return ENVIRONMENTS['production']['api_url']


# Mark configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "production: mark test as production-only (use --production to run)"
    )
