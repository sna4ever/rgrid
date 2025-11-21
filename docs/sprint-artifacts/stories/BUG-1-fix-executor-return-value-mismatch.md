# Story BUG-1: Fix Executor Return Value Mismatch

Status: ready-for-dev (P1 - Blocking job execution)

## Story

As a platform operator,
I want the executor return values to match the worker's expectations,
So that jobs can execute successfully on provisioned workers.

## Bug Description

**Error**: `ValueError: too many values to unpack (expected 3)`

**Location**: `runner/runner/worker.py:156`

**Root Cause**: The deployed Docker image (`ghcr.io/sna4ever/rgrid-worker:latest`) contains an older version of `worker.py` that expects 3 return values from `execute_script()`, but the current `executor.py` returns 4 values.

**Evidence** (from worker logs):
```
2025-11-21 16:12:20,956 - __main__ - ERROR - Error processing exec_...: too many values to unpack (expected 3)
Traceback (most recent call last):
  File "/app/runner/runner/worker.py", line 156, in process_job
    exit_code, stdout, stderr = self.executor.execute_script(
    ^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: too many values to unpack (expected 3)
```

**Current executor.py returns**: `(exit_code, output, "", uploaded_outputs)` - 4 values
**Old worker.py expects**: `(exit_code, stdout, stderr)` - 3 values
**Current worker.py expects**: `(exit_code, stdout, stderr, uploaded_outputs)` - 4 values

## Acceptance Criteria

1. **Given** the latest code is deployed to the Docker image
2. **When** a worker processes a job
3. **Then** the job executes successfully without ValueError

## Tasks / Subtasks

- [ ] Task 1: Rebuild and push Docker image with latest code
  - [ ] Trigger GitHub Actions workflow to rebuild `ghcr.io/sna4ever/rgrid-worker:latest`
  - [ ] Verify new image contains updated `worker.py` (line 156 should unpack 4 values)
  - [ ] Wait for image to be available in GHCR

- [ ] Task 2: Test fix on staging
  - [ ] Delete existing workers from Hetzner
  - [ ] Submit test job to trigger new worker provisioning
  - [ ] Verify worker pulls new image and executes jobs successfully

- [ ] Task 3: Cleanup
  - [ ] Mark any stuck jobs as failed in database
  - [ ] Delete old/zombie workers from database

## Dev Notes

### Root Cause Analysis

The Docker image was built before Story 7-6 (Large File Streaming) was merged, which added the `uploaded_outputs` return value to `execute_script()`. The image needs to be rebuilt with the latest code.

### Fix Steps

1. Push any uncommitted changes to trigger image rebuild
2. OR manually trigger the `build-worker.yml` GitHub Action
3. Wait for new image to be available
4. New workers will automatically pull the updated image

### Verification

After fix, worker logs should show:
```
INFO - Claimed job: <execution_id>
INFO - Processing <execution_id>: python:3.11
INFO - Job completed successfully
```

Instead of:
```
ERROR - Error processing <execution_id>: too many values to unpack (expected 3)
```

## Related

- Story 7-6: Implement Large File Streaming and Compression (introduced the 4th return value)
- Private Network Deployment (discovered during testing)

## Dev Agent Record

### Context Reference

- Bug discovered during private network deployment testing
- Worker successfully connected to database via private network (10.0.1.2)
- Worker claimed jobs but failed during execution due to version mismatch

### Estimated Effort

- 15 minutes: Trigger image rebuild
- 5 minutes: Verify fix
- 10 minutes: Cleanup stuck jobs

**Total**: ~30 minutes
