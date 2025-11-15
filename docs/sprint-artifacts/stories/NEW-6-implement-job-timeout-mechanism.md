# Story NEW-6: Implement Job Timeout Mechanism

Status: done (Completed: 2025-11-15, Tier 3)

## Story

As a platform operator,
I want jobs to be killed if they exceed a timeout,
So that hung jobs don't run forever and waste resources.

## Acceptance Criteria

1. **Given** a job is submitted for execution
2. **When** the job runs longer than the configured timeout
3. **Then** the system automatically terminates the job:
   - Default timeout: 300 seconds (5 minutes)
   - Timeout is configurable per job
   - Container killed if timeout exceeded
   - Clear error message returned indicating timeout
   - Exit code -1 for timed-out jobs

## Tasks / Subtasks

- [x] Task 1: Add timeout parameter (AC: #1, #2)
  - [x] Add `timeout_seconds` parameter to execute_script()
  - [x] Set default to 300 seconds (5 minutes)
  - [x] Document timeout behavior

- [x] Task 2: Implement timeout enforcement (AC: #3, #4)
  - [x] Wrap container.wait() with timeout
  - [x] Catch timeout exceptions
  - [x] Kill container on timeout
  - [x] Remove killed container
  - [x] Return clear error message

- [x] Task 3: Test timeout mechanism (AC: #5)
  - [x] Write integration tests for quick scripts
  - [x] Write integration tests for timed-out scripts
  - [x] Verify timeout is configurable
  - [x] Verify error messages are clear

## Dev Notes

### Prerequisites

- DockerExecutor exists (Story 2-2)
- Container execution working (Story 2-2)
- Resource limits implemented (Story NEW-5)

### Technical Notes

**Timeout Implementation**:
```python
# Wait for completion with timeout
try:
    result = container.wait(timeout=timeout_seconds)
    exit_code = result.get("StatusCode", -1)
except Exception as timeout_error:
    # Timeout or other error - kill container
    container.kill()
    container.remove()
    return -1, "", f"Execution timeout ({timeout_seconds}s) or error: {str(timeout_error)}"
```

**Timeout Behavior**:
- Container.wait() blocks until container stops OR timeout
- On timeout: Docker exception raised
- Cleanup: Kill container, remove it, return error
- Exit code: -1 (indicates error/timeout)

**Error Message Format**:
```
Execution timeout (300s) or error: ...
```

**Design Decisions**:
- Default 300s = 5 minutes (reasonable for most tasks)
- Timeout applied at container level (not script level)
- Kill signal ensures immediate termination
- Container removed to prevent accumulation

### References

- [Source: docs/TIER3_PLAN.md - Story NEW-6]
- [Source: docs/architecture.md - Job reliability]
- [Docker SDK container.wait()](https://docker-py.readthedocs.io/en/stable/containers.html)

## Dev Agent Record

### Context Reference

- Story completed as part of Tier 3 batch implementation
- Closely related to NEW-5 (resource limits)

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Implementation Summary

**Files Modified**:
- `runner/runner/executor.py`
  - Added `timeout_seconds` parameter (default: 300)
  - Wrapped container.wait() with try/except
  - Added timeout exception handling
  - Kill and remove container on timeout
  - Return clear error message with duration

**Code Changes**:
```python
# Before:
result = container.wait()

# After:
try:
    result = container.wait(timeout=timeout_seconds)
    exit_code = result.get("StatusCode", -1)
except Exception as timeout_error:
    container.kill()
    container.remove()
    return -1, "", f"Execution timeout ({timeout_seconds}s)..."
```

**Testing**:
- **Automated**: 14 integration tests (shared with NEW-5)
  - `tests/integration/test_tier3_resource_limits.py`
  - Tests quick scripts complete before timeout
  - Tests long scripts killed by timeout
  - Tests timeout is configurable
  - Tests error messages are clear
  - Tests timeout works with resource limits
  - All tests passing (14/14)

**Test Coverage**:
```python
test_quick_script_completes_before_timeout()      # ✅
test_timeout_kills_long_running_script()          # ✅
test_timeout_parameter_is_configurable()          # ✅
test_timeout_error_message_is_clear()             # ✅
test_default_timeout_is_300_seconds()             # ✅
```

### Completion Notes

✅ Timeout mechanism implemented (300s default)
✅ Containers killed when exceeding timeout
✅ Clear error messages with duration
✅ Timeout configurable per job
✅ Integration tests verify behavior
✅ No more hung jobs running forever

**Production Impact**:
- Prevents hung jobs from running indefinitely
- Protects system resources from stuck containers
- Clear feedback when jobs timeout
- Configurable for different job types (quick vs. long)

**Real-world Usage**:
```bash
# Quick job - completes normally
execute_script(script, timeout_seconds=10)

# Long-running job - needs more time
execute_script(script, timeout_seconds=3600)  # 1 hour

# Use default
execute_script(script)  # 300s = 5 minutes
```

**Known Behavior**:
- Stdout may be incomplete if killed mid-output
- Container killed immediately (SIGKILL, no graceful shutdown)
- This is by design - hung jobs need forceful termination

### File List

**Modified**:
- runner/runner/executor.py:23 (added parameter)
- runner/runner/executor.py:73-82 (timeout enforcement)

**Tests Created**:
- tests/integration/test_tier3_resource_limits.py (5 tests for timeout)

**Related Documentation**:
- docs/TIER3_SUMMARY.md
- docs/TIER3_TEST_REPORT.md
