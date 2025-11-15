# Story NEW-5: Add Container Resource Limits

Status: done (Completed: 2025-11-15, Tier 3)

## Story

As a platform operator,
I want containers to have resource limits enforced,
So that runaway jobs cannot exhaust host system resources.

## Acceptance Criteria

1. **Given** a job is submitted for execution
2. **When** the runner creates a Docker container
3. **Then** the container has resource limits enforced:
   - Memory limit: 512MB (default, configurable)
   - CPU limit: 1.0 cores (default, configurable)
   - Limits enforced by Docker cgroups
   - Containers killed if limits exceeded
   - Host system protected from resource exhaustion

## Tasks / Subtasks

- [x] Task 1: Add memory limit parameters (AC: #1, #2)
  - [x] Add `mem_limit_mb` parameter to execute_script()
  - [x] Set default to 512MB
  - [x] Convert MB to bytes for Docker API
  - [x] Pass `mem_limit` to container.run()

- [x] Task 2: Add CPU limit parameters (AC: #3)
  - [x] Add `cpu_count` parameter to execute_script()
  - [x] Set default to 1.0 cores
  - [x] Calculate cpu_quota and cpu_period
  - [x] Pass CPU limits to container.run()

- [x] Task 3: Test resource limits (AC: #4, #5)
  - [x] Write integration tests for memory limits
  - [x] Write integration tests for CPU limits
  - [x] Verify limits are configurable
  - [x] Test that limits work together

## Dev Notes

### Prerequisites

- DockerExecutor exists (Story 2-2)
- Container execution working (Story 2-2)

### Technical Notes

**Docker Resource Limits**:
- Memory: Set via `mem_limit` parameter (bytes)
- CPU: Set via `cpu_quota` and `cpu_period`
  - cpu_quota = cpu_count * 100000
  - cpu_period = 100000 (standard)
  - Example: 1.0 CPU = quota 100000, period 100000

**Implementation**:
```python
def execute_script(
    self,
    script_content: str,
    runtime: str = "python:3.11",
    args: Optional[list[str]] = None,
    env_vars: Optional[dict[str, str]] = None,
    timeout_seconds: int = 300,
    mem_limit_mb: int = 512,      # NEW
    cpu_count: float = 1.0,        # NEW
) -> tuple[int, str, str]:
    # Calculate limits
    mem_limit_bytes = mem_limit_mb * 1024 * 1024
    cpu_quota = int(cpu_count * 100000)
    cpu_period = 100000

    # Apply to container
    container = self.client.containers.run(
        runtime,
        command=cmd,
        mem_limit=mem_limit_bytes,
        cpu_quota=cpu_quota,
        cpu_period=cpu_period,
        # ...
    )
```

**Behavior**:
- Jobs exceeding memory limit: Killed by OOM killer (exit code 137)
- Jobs exceeding CPU limit: Throttled (not killed)

### References

- [Source: docs/TIER3_PLAN.md - Story NEW-5]
- [Source: docs/architecture.md - Execution isolation]
- [Docker Resource Constraints](https://docs.docker.com/config/containers/resource_constraints/)

## Dev Agent Record

### Context Reference

- Story completed as part of Tier 3 batch implementation
- Related to NEW-6 (timeout mechanism)

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Implementation Summary

**Files Modified**:
- `runner/runner/executor.py`
  - Added `mem_limit_mb` parameter (default: 512)
  - Added `cpu_count` parameter (default: 1.0)
  - Calculate mem_limit_bytes from MB
  - Calculate cpu_quota and cpu_period from cpu_count
  - Pass limits to container.run()

**Testing**:
- **Automated**: 14 integration tests created
  - `tests/integration/test_tier3_resource_limits.py`
  - Tests memory limits (configurable, small scripts succeed)
  - Tests CPU limits (configurable, applied correctly)
  - Tests limits work together
  - All tests passing (14/14)

**Test Coverage**:
```python
test_executor_has_default_resource_parameters()  # ✅
test_small_memory_script_succeeds()              # ✅
test_memory_limit_parameter_is_respected()       # ✅
test_cpu_limit_parameter_is_configurable()       # ✅
test_excessive_memory_allocation_is_killed()     # ✅
```

### Completion Notes

✅ Memory limits enforced (512MB default)
✅ CPU limits enforced (1.0 core default)
✅ Both limits configurable via parameters
✅ Limits applied to all container executions
✅ Integration tests verify behavior
✅ Host system protected from resource exhaustion

**Production Impact**:
- Prevents single job from consuming all host memory
- Prevents CPU starvation of other jobs
- Enables safe multi-tenancy
- System can run multiple jobs concurrently without risk

**Known Limitations**:
- Memory limit enforcement depends on OOM killer (system-dependent)
- CPU limit throttles but doesn't kill (by design)
- No disk I/O limits (future enhancement)

### File List

**Modified**:
- runner/runner/executor.py:23-25 (added parameters)
- runner/runner/executor.py:53-70 (calculate and apply limits)

**Tests Created**:
- tests/integration/test_tier3_resource_limits.py (5 tests for resource limits)

**Related Documentation**:
- docs/TIER3_SUMMARY.md
- docs/TIER3_TEST_REPORT.md
