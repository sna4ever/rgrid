"""
Performance tests for RGrid CLI commands.

Tests verify CLI response times against OPUS.md target:
- CLI response time: < 500ms for all commands

Usage:
    # Run CLI performance tests
    pytest tests/performance/test_cli_performance.py -v -s
"""

import os
import time
import subprocess
import statistics
from typing import List, Tuple, Optional
import pytest


# Configuration
CLI_PATH = "rgrid"  # Assumes rgrid is in PATH or use full path
VENV_PYTHON = os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python")
CLI_MODULE = "cli.rgrid.main"

# SLA Target
SLA_CLI_RESPONSE = 0.5  # 500ms


def run_cli_command(args: List[str], timeout: float = 30) -> Tuple[float, int, str, str]:
    """Run a CLI command and measure time.

    Returns: (elapsed_time, return_code, stdout, stderr)
    """
    start = time.perf_counter()
    try:
        # Try running as module first (development)
        cmd = [VENV_PYTHON, "-m", CLI_MODULE] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, 'RGRID_API_URL': os.getenv('RGRID_API_URL', 'https://staging.rgrid.dev/api/v1')}
        )
        elapsed = time.perf_counter() - start
        return elapsed, result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return elapsed, -1, "", "Command timed out"
    except FileNotFoundError:
        # Try running as installed command
        try:
            cmd = [CLI_PATH] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'RGRID_API_URL': os.getenv('RGRID_API_URL', 'https://staging.rgrid.dev/api/v1')}
            )
            elapsed = time.perf_counter() - start
            return elapsed, result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            elapsed = time.perf_counter() - start
            return elapsed, -1, "", "CLI not found"


class CLIMetrics:
    """Track CLI command performance metrics."""

    def __init__(self, command: str):
        self.command = command
        self.response_times: List[float] = []
        self.return_codes: List[int] = []
        self.errors: List[str] = []

    def add_sample(self, elapsed: float, return_code: int, stderr: str = ""):
        self.response_times.append(elapsed)
        self.return_codes.append(return_code)
        if return_code != 0 and stderr:
            self.errors.append(stderr[:100])

    @property
    def mean(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0

    @property
    def p95(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def success_rate(self) -> float:
        if not self.return_codes:
            return 0
        # Consider 0 and 1 (usage error) as "working"
        # Non-zero may be expected for some commands
        working = sum(1 for rc in self.return_codes if rc in [0, 1, 2])
        return working / len(self.return_codes)

    def summary(self) -> str:
        if not self.response_times:
            return f"{self.command}: No samples"
        return (
            f"{self.command}:\n"
            f"  Samples: {len(self.response_times)}\n"
            f"  Mean: {self.mean*1000:.0f}ms, P95: {self.p95*1000:.0f}ms\n"
            f"  Min: {min(self.response_times)*1000:.0f}ms, "
            f"Max: {max(self.response_times)*1000:.0f}ms"
        )


class TestCLIStartupPerformance:
    """Test CLI startup and help command performance."""

    def test_help_command_under_sla(self):
        """rgrid --help should complete under 500ms SLA."""
        elapsed, rc, stdout, stderr = run_cli_command(["--help"])

        print(f"\n  rgrid --help: {elapsed*1000:.0f}ms (rc={rc})")

        # Help should work and be fast
        assert elapsed < SLA_CLI_RESPONSE, (
            f"Help command exceeded SLA: {elapsed*1000:.0f}ms > {SLA_CLI_RESPONSE*1000:.0f}ms"
        )

    def test_version_command_under_sla(self):
        """rgrid --version should complete under 500ms SLA."""
        elapsed, rc, stdout, stderr = run_cli_command(["--version"])

        print(f"\n  rgrid --version: {elapsed*1000:.0f}ms (rc={rc})")

        assert elapsed < SLA_CLI_RESPONSE, (
            f"Version command exceeded SLA: {elapsed*1000:.0f}ms > {SLA_CLI_RESPONSE*1000:.0f}ms"
        )

    def test_repeated_help_commands(self):
        """Help command should be consistently fast."""
        metrics = CLIMetrics("rgrid --help")

        for _ in range(5):
            elapsed, rc, stdout, stderr = run_cli_command(["--help"])
            metrics.add_sample(elapsed, rc, stderr)

        print(f"\n  {metrics.summary()}")

        assert metrics.p95 < SLA_CLI_RESPONSE, (
            f"Help p95 exceeded SLA: {metrics.p95*1000:.0f}ms"
        )


class TestCLISubcommandPerformance:
    """Test individual CLI subcommand performance."""

    def test_status_help_under_sla(self):
        """rgrid status --help should be fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["status", "--help"])

        print(f"\n  rgrid status --help: {elapsed*1000:.0f}ms (rc={rc})")

        assert elapsed < SLA_CLI_RESPONSE, (
            f"Status help exceeded SLA: {elapsed*1000:.0f}ms"
        )

    def test_logs_help_under_sla(self):
        """rgrid logs --help should be fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["logs", "--help"])

        print(f"\n  rgrid logs --help: {elapsed*1000:.0f}ms (rc={rc})")

        assert elapsed < SLA_CLI_RESPONSE, (
            f"Logs help exceeded SLA: {elapsed*1000:.0f}ms"
        )

    def test_cost_help_under_sla(self):
        """rgrid cost --help should be fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["cost", "--help"])

        print(f"\n  rgrid cost --help: {elapsed*1000:.0f}ms (rc={rc})")

        assert elapsed < SLA_CLI_RESPONSE, (
            f"Cost help exceeded SLA: {elapsed*1000:.0f}ms"
        )

    def test_run_help_under_sla(self):
        """rgrid run --help should be fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["run", "--help"])

        print(f"\n  rgrid run --help: {elapsed*1000:.0f}ms (rc={rc})")

        assert elapsed < SLA_CLI_RESPONSE, (
            f"Run help exceeded SLA: {elapsed*1000:.0f}ms"
        )


class TestCLIStatusCommand:
    """Test status command performance with real API."""

    def test_status_nonexistent_id(self):
        """Status for non-existent ID should fail fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["status", "nonexistent-id-12345"])

        print(f"\n  rgrid status <bad-id>: {elapsed*1000:.0f}ms (rc={rc})")

        # Should fail but still be fast
        assert elapsed < 2.0, (  # More lenient for network request
            f"Status command too slow: {elapsed*1000:.0f}ms"
        )


class TestCLICostCommand:
    """Test cost command performance."""

    def test_cost_summary_performance(self):
        """Cost summary should complete reasonably fast."""
        elapsed, rc, stdout, stderr = run_cli_command(["cost", "--days", "7"])

        print(f"\n  rgrid cost --days 7: {elapsed*1000:.0f}ms (rc={rc})")
        if stdout:
            print(f"  Output preview: {stdout[:200]}...")

        # Cost command involves API call, so allow more time
        assert elapsed < 3.0, (
            f"Cost command too slow: {elapsed*1000:.0f}ms"
        )


class TestCLIOverallPerformance:
    """Test overall CLI performance characteristics."""

    def test_all_help_commands_under_sla(self):
        """All --help commands should complete under 500ms."""
        commands = [
            ["--help"],
            ["run", "--help"],
            ["status", "--help"],
            ["logs", "--help"],
            ["cost", "--help"],
            ["retry", "--help"],
        ]

        results = []
        for args in commands:
            elapsed, rc, stdout, stderr = run_cli_command(args)
            cmd_str = " ".join(["rgrid"] + args)
            results.append({
                'command': cmd_str,
                'elapsed_ms': elapsed * 1000,
                'return_code': rc,
                'within_sla': elapsed < SLA_CLI_RESPONSE
            })

        print("\n  CLI Help Command Performance:")
        print("  " + "-" * 50)
        for r in results:
            sla = "OK" if r['within_sla'] else "SLOW"
            print(f"  {r['command']:30} {r['elapsed_ms']:6.0f}ms [{sla}]")
        print("  " + "-" * 50)

        all_within_sla = all(r['within_sla'] for r in results)
        assert all_within_sla, "Some help commands exceeded SLA"

    def test_cli_cold_vs_warm_start(self):
        """Compare cold start vs warm start performance."""
        # Cold start (first run)
        cold_times = []
        for _ in range(3):
            elapsed, rc, stdout, stderr = run_cli_command(["--help"])
            cold_times.append(elapsed)

        # Warm start (subsequent runs)
        warm_times = []
        for _ in range(5):
            elapsed, rc, stdout, stderr = run_cli_command(["--help"])
            warm_times.append(elapsed)

        print(f"\n  CLI Startup Performance:")
        print(f"    Cold start avg: {statistics.mean(cold_times)*1000:.0f}ms")
        print(f"    Warm start avg: {statistics.mean(warm_times)*1000:.0f}ms")

        # Both should be under SLA
        assert statistics.mean(warm_times) < SLA_CLI_RESPONSE, (
            f"Warm start too slow: {statistics.mean(warm_times)*1000:.0f}ms"
        )
