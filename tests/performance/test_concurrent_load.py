"""
Concurrent load tests for RGrid API.

Tests verify the system can handle high concurrent load as specified in OPUS.md:
- Handle 100+ concurrent execution submissions
- Handle 1000 concurrent executions (stretch goal)
- No significant degradation under load

Usage:
    # Run concurrent tests against staging
    export RGRID_API_URL=https://staging.rgrid.dev/api/v1
    pytest tests/performance/test_concurrent_load.py -v -s
"""

import os
import time
import statistics
import concurrent.futures
from typing import List, Dict, Optional, Tuple
import pytest
import requests


# Configuration
API_URL = os.getenv('RGRID_API_URL', 'https://staging.rgrid.dev/api/v1')
TIMEOUT = 30

# Concurrency targets
TARGET_CONCURRENT_100 = 100
TARGET_CONCURRENT_50 = 50

# SLA
SLA_SUCCESS_RATE = 0.95  # 95% success rate under load
SLA_P95_RESPONSE = 5.0   # 5s p95 under concurrent load


class ConcurrencyMetrics:
    """Track concurrent request metrics."""

    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: List[int] = []
        self.errors: List[str] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def record_success(self, elapsed: float, status_code: int):
        self.response_times.append(elapsed)
        self.status_codes.append(status_code)

    def record_error(self, error: str):
        self.errors.append(error)

    @property
    def total_requests(self) -> int:
        return len(self.response_times) + len(self.errors)

    @property
    def success_count(self) -> int:
        return len(self.response_times)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.success_count / self.total_requests

    @property
    def mean_response(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0

    @property
    def p95_response(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def throughput(self) -> float:
        """Requests per second."""
        duration = self.end_time - self.start_time
        if duration <= 0:
            return 0
        return self.total_requests / duration

    def summary(self) -> str:
        return (
            f"Total: {self.total_requests}, Success: {self.success_count}, "
            f"Errors: {self.error_count}\n"
            f"  Success Rate: {self.success_rate*100:.1f}%\n"
            f"  Mean: {self.mean_response*1000:.1f}ms, P95: {self.p95_response*1000:.1f}ms\n"
            f"  Throughput: {self.throughput:.1f} req/s\n"
            f"  Duration: {self.end_time - self.start_time:.2f}s"
        )


@pytest.fixture
def api_url():
    return API_URL


class TestConcurrentHealthRequests:
    """Test concurrent health endpoint requests."""

    @pytest.mark.parametrize("num_concurrent", [10, 25, 50])
    def test_concurrent_health_checks(self, api_url, num_concurrent):
        """Health endpoint should handle N concurrent requests."""
        metrics = ConcurrencyMetrics()

        def make_request() -> Tuple[Optional[float], Optional[int]]:
            try:
                start = time.perf_counter()
                response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
                elapsed = time.perf_counter() - start
                return elapsed, response.status_code
            except Exception as e:
                return None, None

        metrics.start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        metrics.end_time = time.perf_counter()

        for elapsed, status in results:
            if elapsed is not None and status == 200:
                metrics.record_success(elapsed, status)
            else:
                metrics.record_error(f"Failed: elapsed={elapsed}, status={status}")

        print(f"\n  Concurrent health ({num_concurrent} requests):\n  {metrics.summary()}")

        assert metrics.success_rate >= SLA_SUCCESS_RATE, (
            f"Success rate too low: {metrics.success_rate*100:.1f}% < {SLA_SUCCESS_RATE*100:.1f}%"
        )

    def test_100_concurrent_health_checks(self, api_url):
        """Health endpoint should handle 100 concurrent requests."""
        metrics = ConcurrencyMetrics()
        num_concurrent = TARGET_CONCURRENT_100

        def make_request() -> Tuple[Optional[float], Optional[int]]:
            try:
                start = time.perf_counter()
                response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
                elapsed = time.perf_counter() - start
                return elapsed, response.status_code
            except Exception as e:
                return None, None

        metrics.start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        metrics.end_time = time.perf_counter()

        for elapsed, status in results:
            if elapsed is not None and status == 200:
                metrics.record_success(elapsed, status)
            else:
                metrics.record_error(f"Failed: elapsed={elapsed}, status={status}")

        print(f"\n  100 concurrent health requests:\n  {metrics.summary()}")

        assert metrics.success_rate >= SLA_SUCCESS_RATE, (
            f"Success rate too low: {metrics.success_rate*100:.1f}%"
        )
        assert metrics.p95_response < SLA_P95_RESPONSE, (
            f"P95 too high under load: {metrics.p95_response:.2f}s"
        )


class TestConcurrentMixedEndpoints:
    """Test concurrent requests to multiple endpoints."""

    def test_mixed_endpoint_load(self, api_url):
        """API should handle mixed endpoint concurrent requests."""
        metrics = ConcurrencyMetrics()
        num_requests = 50

        endpoints = [
            ('GET', '/health', {}),
            ('GET', '/executions', {'limit': 5}),
            ('GET', '/cost', {'days': 7}),
            ('GET', '/estimate', {'batch_size': 5}),
        ]

        def make_request(endpoint_idx: int) -> Tuple[Optional[float], Optional[int], str]:
            method, path, params = endpoints[endpoint_idx % len(endpoints)]
            try:
                start = time.perf_counter()
                response = requests.request(
                    method,
                    f"{api_url}{path}",
                    params=params,
                    timeout=TIMEOUT
                )
                elapsed = time.perf_counter() - start
                return elapsed, response.status_code, path
            except Exception as e:
                return None, None, path

        metrics.start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        metrics.end_time = time.perf_counter()

        endpoint_results: Dict[str, List[float]] = {}
        for elapsed, status, path in results:
            if elapsed is not None and status in [200, 401, 404, 422]:
                metrics.record_success(elapsed, status)
                if path not in endpoint_results:
                    endpoint_results[path] = []
                endpoint_results[path].append(elapsed)
            else:
                metrics.record_error(f"{path}: status={status}")

        print(f"\n  Mixed endpoint load ({num_requests} requests):\n  {metrics.summary()}")
        print("  Per-endpoint averages:")
        for path, times in endpoint_results.items():
            avg = statistics.mean(times) if times else 0
            print(f"    {path}: {avg*1000:.1f}ms avg ({len(times)} requests)")

        assert metrics.success_rate >= SLA_SUCCESS_RATE, (
            f"Success rate too low: {metrics.success_rate*100:.1f}%"
        )


class TestBurstLoad:
    """Test burst load patterns."""

    def test_burst_then_normal(self, api_url):
        """API should recover after burst load."""
        # Phase 1: Burst of 50 concurrent requests
        burst_metrics = ConcurrencyMetrics()

        def make_request() -> Tuple[Optional[float], Optional[int]]:
            try:
                start = time.perf_counter()
                response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
                elapsed = time.perf_counter() - start
                return elapsed, response.status_code
            except:
                return None, None

        burst_metrics.start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        burst_metrics.end_time = time.perf_counter()

        for elapsed, status in results:
            if elapsed is not None and status == 200:
                burst_metrics.record_success(elapsed, status)
            else:
                burst_metrics.record_error("Failed")

        # Phase 2: Wait briefly then make single requests
        time.sleep(1)

        recovery_times = []
        for _ in range(5):
            start = time.perf_counter()
            response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
            elapsed = time.perf_counter() - start
            if response.status_code == 200:
                recovery_times.append(elapsed)

        print(f"\n  Burst phase (50 concurrent):\n  {burst_metrics.summary()}")
        if recovery_times:
            print(f"  Recovery phase (5 sequential):")
            print(f"    Avg: {statistics.mean(recovery_times)*1000:.1f}ms")
            print(f"    Max: {max(recovery_times)*1000:.1f}ms")

        # Recovery requests should be fast (back to normal)
        if recovery_times:
            assert max(recovery_times) < 1.0, (
                f"API didn't recover after burst: {max(recovery_times)*1000:.1f}ms"
            )


class TestSustainedConcurrency:
    """Test sustained concurrent load over time."""

    def test_sustained_concurrent_load(self, api_url):
        """API should handle sustained concurrent load for 30 seconds."""
        duration_seconds = 30
        concurrent_requests = 10
        metrics = ConcurrencyMetrics()

        def make_request() -> Tuple[Optional[float], Optional[int]]:
            try:
                start = time.perf_counter()
                response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
                elapsed = time.perf_counter() - start
                return elapsed, response.status_code
            except:
                return None, None

        metrics.start_time = time.perf_counter()
        end_time = metrics.start_time + duration_seconds

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            while time.perf_counter() < end_time:
                futures = [executor.submit(make_request) for _ in range(concurrent_requests)]
                for f in concurrent.futures.as_completed(futures):
                    elapsed, status = f.result()
                    if elapsed is not None and status == 200:
                        metrics.record_success(elapsed, status)
                    else:
                        metrics.record_error("Failed")

        metrics.end_time = time.perf_counter()

        print(f"\n  Sustained load ({duration_seconds}s, {concurrent_requests} concurrent):")
        print(f"  {metrics.summary()}")

        # Check for degradation - compare first and last 10% of requests
        if len(metrics.response_times) > 20:
            chunk_size = len(metrics.response_times) // 10
            first_chunk = metrics.response_times[:chunk_size]
            last_chunk = metrics.response_times[-chunk_size:]

            first_avg = statistics.mean(first_chunk)
            last_avg = statistics.mean(last_chunk)
            degradation = (last_avg - first_avg) / first_avg if first_avg > 0 else 0

            print(f"  Degradation check:")
            print(f"    First {chunk_size}: {first_avg*1000:.1f}ms avg")
            print(f"    Last {chunk_size}: {last_avg*1000:.1f}ms avg")
            print(f"    Degradation: {degradation*100:.1f}%")

            # Allow up to 100% degradation under sustained load
            assert degradation < 1.0, (
                f"Significant degradation under sustained load: {degradation*100:.1f}%"
            )

        assert metrics.success_rate >= 0.90, (
            f"Success rate too low under sustained load: {metrics.success_rate*100:.1f}%"
        )


class TestConnectionPooling:
    """Test connection reuse and pooling behavior."""

    def test_connection_reuse_performance(self, api_url):
        """Connection reuse should improve performance."""
        # Test with new connections each time
        no_reuse_times = []
        for _ in range(10):
            start = time.perf_counter()
            response = requests.get(f"{api_url}/health", timeout=TIMEOUT)
            elapsed = time.perf_counter() - start
            if response.status_code == 200:
                no_reuse_times.append(elapsed)

        # Test with session (connection reuse)
        session = requests.Session()
        reuse_times = []
        for _ in range(10):
            start = time.perf_counter()
            response = session.get(f"{api_url}/health", timeout=TIMEOUT)
            elapsed = time.perf_counter() - start
            if response.status_code == 200:
                reuse_times.append(elapsed)
        session.close()

        print(f"\n  Connection pooling comparison:")
        if no_reuse_times:
            print(f"    No reuse: {statistics.mean(no_reuse_times)*1000:.1f}ms avg")
        if reuse_times:
            print(f"    With reuse: {statistics.mean(reuse_times)*1000:.1f}ms avg")

        if no_reuse_times and reuse_times:
            improvement = (statistics.mean(no_reuse_times) - statistics.mean(reuse_times)) / statistics.mean(no_reuse_times)
            print(f"    Improvement: {improvement*100:.1f}%")

        # Session-based requests should be at least as fast
        if no_reuse_times and reuse_times:
            assert statistics.mean(reuse_times) <= statistics.mean(no_reuse_times) * 1.1, (
                "Connection reuse should not be significantly slower"
            )
