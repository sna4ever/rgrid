"""
Performance tests for RGrid API endpoints.

Tests verify API response times against SLA targets from OPUS.md:
- API response time: < 2s for all endpoints
- High-throughput endpoints: < 500ms p95

Usage:
    # Run performance tests against staging
    export RGRID_API_URL=https://staging.rgrid.dev/api/v1
    pytest tests/performance/test_api_performance.py -v

    # Run with detailed timing output
    pytest tests/performance/test_api_performance.py -v -s
"""

import os
import time
import statistics
import concurrent.futures
from typing import List, Dict, Tuple
import pytest
import requests


# Configuration
API_URL = os.getenv('RGRID_API_URL', 'https://staging.rgrid.dev/api/v1')
TIMEOUT = 30  # Request timeout in seconds

# SLA Targets (in seconds)
SLA_API_RESPONSE = 2.0  # Max API response time
SLA_HEALTH_P95 = 0.5    # Health endpoint p95
SLA_LIST_P95 = 1.0      # List endpoints p95
SLA_CREATE_P95 = 1.5    # Create endpoints p95


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self):
        self.response_times: List[float] = []
        self.errors: List[str] = []

    def add_sample(self, response_time: float):
        """Add a response time sample."""
        self.response_times.append(response_time)

    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)

    @property
    def count(self) -> int:
        return len(self.response_times)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def mean(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0

    @property
    def median(self) -> float:
        return statistics.median(self.response_times) if self.response_times else 0

    @property
    def p95(self) -> float:
        """95th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def p99(self) -> float:
        """99th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def min(self) -> float:
        return min(self.response_times) if self.response_times else 0

    @property
    def max(self) -> float:
        return max(self.response_times) if self.response_times else 0

    def summary(self) -> str:
        """Return a formatted summary of metrics."""
        return (
            f"Samples: {self.count}, Errors: {self.error_count}\n"
            f"  Min: {self.min*1000:.1f}ms, Max: {self.max*1000:.1f}ms\n"
            f"  Mean: {self.mean*1000:.1f}ms, Median: {self.median*1000:.1f}ms\n"
            f"  P95: {self.p95*1000:.1f}ms, P99: {self.p99*1000:.1f}ms"
        )


def timed_request(method: str, url: str, **kwargs) -> Tuple[float, requests.Response]:
    """Make a timed HTTP request."""
    start = time.perf_counter()
    response = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    elapsed = time.perf_counter() - start
    return elapsed, response


@pytest.fixture
def api_url():
    """Get the API URL."""
    return API_URL


class TestHealthEndpointPerformance:
    """Test health endpoint performance - should be fastest."""

    def test_health_single_request_under_sla(self, api_url):
        """Single health request should complete under 2s SLA."""
        elapsed, response = timed_request('GET', f"{api_url}/health")

        assert response.status_code == 200, f"Health check failed: {response.text}"
        assert elapsed < SLA_API_RESPONSE, (
            f"Health endpoint exceeded SLA: {elapsed:.3f}s > {SLA_API_RESPONSE}s"
        )
        print(f"\n  Health endpoint: {elapsed*1000:.1f}ms")

    def test_health_under_load(self, api_url):
        """Health endpoint should maintain p95 < 500ms under load."""
        metrics = PerformanceMetrics()
        num_requests = 50

        for _ in range(num_requests):
            try:
                elapsed, response = timed_request('GET', f"{api_url}/health")
                if response.status_code == 200:
                    metrics.add_sample(elapsed)
                else:
                    metrics.add_error(f"Status {response.status_code}")
            except Exception as e:
                metrics.add_error(str(e))

        print(f"\n  Health endpoint load test:\n  {metrics.summary()}")

        assert metrics.error_count == 0, f"Errors during load test: {metrics.errors}"
        assert metrics.p95 < SLA_HEALTH_P95, (
            f"Health p95 exceeded SLA: {metrics.p95*1000:.1f}ms > {SLA_HEALTH_P95*1000:.1f}ms"
        )

    def test_health_concurrent_requests(self, api_url):
        """Health endpoint should handle 50 concurrent requests."""
        metrics = PerformanceMetrics()
        num_concurrent = 50

        def make_request():
            try:
                elapsed, response = timed_request('GET', f"{api_url}/health")
                return elapsed if response.status_code == 200 else None
            except Exception:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for result in results:
            if result is not None:
                metrics.add_sample(result)
            else:
                metrics.add_error("Request failed")

        print(f"\n  Health concurrent test ({num_concurrent} requests):\n  {metrics.summary()}")

        success_rate = metrics.count / num_concurrent
        assert success_rate >= 0.95, f"Success rate too low: {success_rate*100:.1f}%"
        assert metrics.p95 < SLA_API_RESPONSE, (
            f"Concurrent p95 exceeded SLA: {metrics.p95*1000:.1f}ms"
        )


class TestExecutionsEndpointPerformance:
    """Test executions endpoint performance."""

    def test_list_executions_under_sla(self, api_url):
        """List executions should complete under 2s SLA."""
        elapsed, response = timed_request(
            'GET',
            f"{api_url}/executions",
            params={'limit': 10}
        )

        # 401 is expected without auth, but should still be fast
        assert response.status_code in [200, 401, 422], (
            f"Unexpected status: {response.status_code}"
        )
        assert elapsed < SLA_API_RESPONSE, (
            f"List executions exceeded SLA: {elapsed:.3f}s > {SLA_API_RESPONSE}s"
        )
        print(f"\n  List executions: {elapsed*1000:.1f}ms (status: {response.status_code})")

    def test_list_executions_repeated(self, api_url):
        """List executions p95 should be under 1s."""
        metrics = PerformanceMetrics()
        num_requests = 20

        for _ in range(num_requests):
            try:
                elapsed, response = timed_request(
                    'GET',
                    f"{api_url}/executions",
                    params={'limit': 10}
                )
                if response.status_code in [200, 401, 422]:
                    metrics.add_sample(elapsed)
                else:
                    metrics.add_error(f"Status {response.status_code}")
            except Exception as e:
                metrics.add_error(str(e))

        print(f"\n  List executions repeated:\n  {metrics.summary()}")

        assert metrics.p95 < SLA_LIST_P95, (
            f"List p95 exceeded SLA: {metrics.p95*1000:.1f}ms > {SLA_LIST_P95*1000:.1f}ms"
        )


class TestCostEndpointPerformance:
    """Test cost endpoint performance."""

    def test_cost_estimate_under_sla(self, api_url):
        """Cost estimate should complete under 2s SLA."""
        elapsed, response = timed_request(
            'GET',
            f"{api_url}/estimate",
            params={'batch_size': 10}
        )

        assert response.status_code in [200, 401, 422], (
            f"Unexpected status: {response.status_code}"
        )
        assert elapsed < SLA_API_RESPONSE, (
            f"Cost estimate exceeded SLA: {elapsed:.3f}s > {SLA_API_RESPONSE}s"
        )
        print(f"\n  Cost estimate: {elapsed*1000:.1f}ms (status: {response.status_code})")

    def test_cost_aggregation_under_sla(self, api_url):
        """Cost aggregation should complete under 2s SLA."""
        elapsed, response = timed_request(
            'GET',
            f"{api_url}/cost",
            params={'days': 30}
        )

        assert response.status_code in [200, 401, 422], (
            f"Unexpected status: {response.status_code}"
        )
        assert elapsed < SLA_API_RESPONSE, (
            f"Cost aggregation exceeded SLA: {elapsed:.3f}s > {SLA_API_RESPONSE}s"
        )
        print(f"\n  Cost aggregation: {elapsed*1000:.1f}ms (status: {response.status_code})")


class TestInputCachePerformance:
    """Test input cache endpoint performance."""

    def test_cache_lookup_under_sla(self, api_url):
        """Cache lookup should be very fast (< 500ms)."""
        test_hash = "abc123def456"  # Non-existent hash

        elapsed, response = timed_request(
            'GET',
            f"{api_url}/input-cache/{test_hash}"
        )

        # 404 expected for non-existent hash, 401 without auth
        assert response.status_code in [200, 401, 404], (
            f"Unexpected status: {response.status_code}"
        )
        assert elapsed < SLA_HEALTH_P95, (
            f"Cache lookup too slow: {elapsed:.3f}s > {SLA_HEALTH_P95}s"
        )
        print(f"\n  Cache lookup: {elapsed*1000:.1f}ms (status: {response.status_code})")


class TestBatchEndpointPerformance:
    """Test batch status endpoint performance."""

    def test_batch_status_under_sla(self, api_url):
        """Batch status lookup should complete under 2s SLA."""
        test_batch_id = "test-batch-123"  # Non-existent batch

        elapsed, response = timed_request(
            'GET',
            f"{api_url}/batches/{test_batch_id}/status"
        )

        # 404 expected for non-existent batch, 401 without auth
        assert response.status_code in [200, 401, 404], (
            f"Unexpected status: {response.status_code}"
        )
        assert elapsed < SLA_API_RESPONSE, (
            f"Batch status exceeded SLA: {elapsed:.3f}s > {SLA_API_RESPONSE}s"
        )
        print(f"\n  Batch status: {elapsed*1000:.1f}ms (status: {response.status_code})")


class TestOverallAPIPerformance:
    """Test overall API performance characteristics."""

    def test_all_endpoints_respond_within_sla(self, api_url):
        """All API endpoints should respond within 2s SLA."""
        endpoints = [
            ('GET', '/health', {}),
            ('GET', '/executions', {'limit': 10}),
            ('GET', '/estimate', {'batch_size': 5}),
            ('GET', '/cost', {'days': 7}),
            ('GET', '/input-cache/test123', {}),
            ('GET', '/batches/test123/status', {}),
        ]

        results = []
        for method, path, params in endpoints:
            try:
                elapsed, response = timed_request(
                    method,
                    f"{api_url}{path}",
                    params=params
                )
                results.append({
                    'endpoint': f"{method} {path}",
                    'elapsed_ms': elapsed * 1000,
                    'status': response.status_code,
                    'within_sla': elapsed < SLA_API_RESPONSE
                })
            except Exception as e:
                results.append({
                    'endpoint': f"{method} {path}",
                    'elapsed_ms': None,
                    'status': 'ERROR',
                    'within_sla': False,
                    'error': str(e)
                })

        print("\n  API Performance Summary:")
        print("  " + "-" * 60)
        for r in results:
            sla_marker = "OK" if r['within_sla'] else "FAIL"
            elapsed_str = f"{r['elapsed_ms']:.1f}ms" if r['elapsed_ms'] else "ERROR"
            print(f"  {r['endpoint']:35} {elapsed_str:>10}  [{sla_marker}]")
        print("  " + "-" * 60)

        all_within_sla = all(r['within_sla'] for r in results)
        assert all_within_sla, "Some endpoints exceeded SLA"

    def test_sustained_load_100_requests(self, api_url):
        """API should handle 100 sustained requests without degradation."""
        metrics = PerformanceMetrics()
        num_requests = 100

        for i in range(num_requests):
            try:
                elapsed, response = timed_request('GET', f"{api_url}/health")
                if response.status_code == 200:
                    metrics.add_sample(elapsed)
                else:
                    metrics.add_error(f"Request {i}: status {response.status_code}")
            except Exception as e:
                metrics.add_error(f"Request {i}: {str(e)}")

        print(f"\n  Sustained load test (100 requests):\n  {metrics.summary()}")

        # Check for no significant degradation
        # First 10 vs last 10 should be similar
        if metrics.count >= 20:
            first_10 = statistics.mean(metrics.response_times[:10])
            last_10 = statistics.mean(metrics.response_times[-10:])
            degradation = (last_10 - first_10) / first_10 if first_10 > 0 else 0

            print(f"  First 10 avg: {first_10*1000:.1f}ms, Last 10 avg: {last_10*1000:.1f}ms")
            print(f"  Degradation: {degradation*100:.1f}%")

            # Allow up to 50% degradation under sustained load
            assert degradation < 0.5, f"Significant performance degradation: {degradation*100:.1f}%"

        assert metrics.error_count < num_requests * 0.05, (
            f"Too many errors: {metrics.error_count}/{num_requests}"
        )
        assert metrics.p95 < SLA_API_RESPONSE, (
            f"P95 exceeded SLA under sustained load: {metrics.p95*1000:.1f}ms"
        )
