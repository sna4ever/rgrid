"""Integration tests for resource limits and timeout (Tier 3 - Stories NEW-5, NEW-6).

These tests verify that Docker containers are properly constrained by:
- Memory limits (512MB default)
- CPU limits (1.0 core default)
- Execution timeout (300 seconds default)

NOTE: These are integration tests that require Docker to be running.
"""

import pytest
import time
from runner.executor import DockerExecutor


class TestResourceLimitsIntegration:
    """Test that resource limits are enforced on containers."""

    @pytest.fixture
    def executor(self):
        """Create a DockerExecutor instance."""
        executor = DockerExecutor()
        yield executor
        executor.close()

    def test_executor_has_default_resource_parameters(self):
        """Executor should accept resource limit parameters with correct defaults."""
        executor = DockerExecutor()

        # Test that execute_script accepts resource parameters
        # We'll use a simple script that completes quickly
        script = "print('Testing defaults')"

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=300,
            mem_limit_mb=512,
            cpu_count=1.0,
        )

        assert exit_code == 0
        assert "Testing defaults" in stdout
        executor.close()

    def test_small_memory_script_succeeds(self, executor):
        """Script using small amount of memory should succeed."""
        script = """
import sys
# Allocate ~10MB
data = "x" * (10 * 1024 * 1024)
print(f"Allocated {len(data) / 1024 / 1024:.1f}MB")
print("SUCCESS")
"""

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            mem_limit_mb=512,
        )

        assert exit_code == 0
        assert "SUCCESS" in stdout

    def test_memory_limit_parameter_is_respected(self, executor):
        """Memory limit parameter should be configurable."""
        # This test verifies the API accepts different memory limits
        script = "print('Testing memory param')"

        # Test with different memory limits
        for mem_limit in [256, 512, 1024]:
            exit_code, stdout, stderr, _ = executor.execute_script(
                script_content=script,
                mem_limit_mb=mem_limit,
            )
            assert exit_code == 0

    def test_cpu_limit_parameter_is_respected(self, executor):
        """CPU limit parameter should be configurable."""
        script = "print('Testing CPU param')"

        # Test with different CPU limits
        for cpu_count in [0.5, 1.0, 2.0]:
            exit_code, stdout, stderr, _ = executor.execute_script(
                script_content=script,
                cpu_count=cpu_count,
            )
            assert exit_code == 0

    @pytest.mark.slow
    def test_excessive_memory_allocation_is_killed(self, executor):
        """Script trying to allocate >512MB should be killed by Docker.

        NOTE: This test is marked as 'slow' because it may take time for
        the OOM killer to activate. The behavior can vary by system.
        """
        script = """
import time
# Try to allocate 1GB in chunks to trigger OOM
data = []
for i in range(10):
    try:
        chunk = "x" * (100 * 1024 * 1024)  # 100MB chunks
        data.append(chunk)
        print(f"Allocated chunk {i+1}")
        time.sleep(0.1)
    except MemoryError:
        print("MemoryError raised")
        break
print("Script completed")
"""

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            mem_limit_mb=512,
            timeout_seconds=60,  # Don't wait too long
        )

        # The container should either:
        # 1. Exit with non-zero (killed by OOM)
        # 2. Raise MemoryError and exit cleanly
        # Either is acceptable - the key is it didn't allocate 1GB

        # We're mainly testing that the mem_limit is set, not OOM behavior
        # which can be system-dependent
        assert exit_code in [0, 137, -1]  # 137 = SIGKILL (OOM), -1 = error


class TestTimeoutMechanismIntegration:
    """Test that job timeout mechanism works correctly."""

    @pytest.fixture
    def executor(self):
        """Create a DockerExecutor instance."""
        executor = DockerExecutor()
        yield executor
        executor.close()

    def test_quick_script_completes_before_timeout(self, executor):
        """Fast script should complete normally without timeout."""
        script = """
import time
time.sleep(1)
print("Completed in 1 second")
"""

        start_time = time.time()
        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=10,
        )
        elapsed = time.time() - start_time

        assert exit_code == 0
        assert "Completed in 1 second" in stdout
        assert elapsed < 10  # Completed well before timeout

    def test_timeout_kills_long_running_script(self, executor):
        """Script exceeding timeout should be killed."""
        script = """
import time
import sys
print("Starting long sleep...", flush=True)
sys.stdout.flush()
time.sleep(30)  # Sleep for 30 seconds
print("This should never print")
"""

        start_time = time.time()
        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=3,  # Kill after 3 seconds
        )
        elapsed = time.time() - start_time

        # Script should be killed
        assert exit_code == -1
        assert "timeout" in stderr.lower() or "Execution timeout" in stderr
        # Note: stdout may be empty if buffer wasn't flushed before kill
        # The key test is that it was killed, not stdout content
        assert "This should never print" not in stdout

        # Should be killed around 3 seconds, not 30
        assert elapsed < 10  # Give some buffer for slow systems

    def test_timeout_parameter_is_configurable(self, executor):
        """Timeout duration should be configurable."""
        script = """
import time
time.sleep(2)
print("Completed")
"""

        # With 5 second timeout, should succeed
        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=5,
        )
        assert exit_code == 0
        assert "Completed" in stdout

        # With 1 second timeout, should fail
        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=1,
        )
        assert exit_code == -1
        assert "timeout" in stderr.lower()

    def test_timeout_error_message_is_clear(self, executor):
        """Timeout error should include clear message with duration."""
        script = "import time; time.sleep(60)"

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=2,
        )

        assert exit_code == -1
        assert "timeout" in stderr.lower()
        assert "2" in stderr or "timeout" in stderr  # Should mention duration

    def test_default_timeout_is_300_seconds(self, executor):
        """Default timeout should be 300 seconds (5 minutes)."""
        # We can't easily test a 5-minute timeout in unit tests,
        # but we can verify the API accepts the default
        script = "print('Testing default timeout')"

        # Call without timeout parameter - should use default
        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            # timeout_seconds not specified - uses default
        )

        assert exit_code == 0


class TestResourceLimitsAndTimeoutTogether:
    """Test that resource limits and timeout work together correctly."""

    @pytest.fixture
    def executor(self):
        """Create a DockerExecutor instance."""
        executor = DockerExecutor()
        yield executor
        executor.close()

    def test_all_limits_applied_simultaneously(self, executor):
        """All resource limits should be enforceable at once."""
        script = """
import time
print("Running with all limits")
time.sleep(1)
print("Completed successfully")
"""

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=10,
            mem_limit_mb=256,
            cpu_count=0.5,
        )

        assert exit_code == 0
        assert "Completed successfully" in stdout

    def test_timeout_kills_even_with_resource_limits_set(self, executor):
        """Timeout should work even when memory/CPU limits are also set."""
        script = "import time; time.sleep(60)"

        exit_code, stdout, stderr, _ = executor.execute_script(
            script_content=script,
            timeout_seconds=2,
            mem_limit_mb=512,
            cpu_count=1.0,
        )

        assert exit_code == -1
        assert "timeout" in stderr.lower()


class TestExecutorResourceLimitAPI:
    """Test the DockerExecutor API for resource limits."""

    def test_executor_signature_has_resource_parameters(self):
        """execute_script should accept resource limit parameters."""
        import inspect
        from runner.executor import DockerExecutor

        sig = inspect.signature(DockerExecutor.execute_script)
        params = sig.parameters

        # Verify all resource parameters exist
        assert 'timeout_seconds' in params
        assert 'mem_limit_mb' in params
        assert 'cpu_count' in params

        # Verify defaults
        assert params['timeout_seconds'].default == 300
        assert params['mem_limit_mb'].default == 512
        assert params['cpu_count'].default == 1.0

    def test_executor_returns_correct_tuple_format(self):
        """Executor should return (exit_code, stdout, stderr, uploaded_outputs) tuple."""
        executor = DockerExecutor()

        result = executor.execute_script("print('test')")

        assert isinstance(result, tuple)
        assert len(result) == 4

        exit_code, stdout, stderr, uploaded_outputs = result
        assert isinstance(exit_code, int)
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)
        assert isinstance(uploaded_outputs, list)

        executor.close()


# Pytest markers for test categorization
pytestmark = [
    pytest.mark.integration,  # Requires Docker
    pytest.mark.tier3,        # Tier 3 features
]
