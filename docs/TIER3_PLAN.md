# Tier 3 Plan: MVP - Production-Ready

**Date**: 2025-11-15
**Goal**: Transform RGrid from demo-ready to production-ready MVP
**Target**: Production-grade reliability, better UX, minimal ops overhead

## Tier 3 Objectives

### Primary Goal: Production Readiness
Make RGrid safe and reliable enough for real workloads:
- ✅ Safe schema evolution (database migrations)
- ✅ Resource protection (prevent runaway containers)
- ✅ Job reliability (timeouts, dead worker detection)
- ✅ Better error messages (actionable feedback)

### Secondary Goal: Developer Experience
Make RGrid easier to use:
- ✅ Pre-configured runtimes (no need to specify python:3.11)
- ✅ Auto-detect dependencies (parse requirements.txt)
- ✅ Better CLI feedback

## Stories for Tier 3

### Core Reliability (MUST HAVE)

#### Story NEW-3: Set Up Alembic Database Migrations
**Epic**: Infrastructure
**Priority**: Critical
**Estimate**: 2 hours

**Why**: Currently dropping/recreating tables manually. Need safe schema evolution.

**Acceptance Criteria**:
- [ ] Alembic installed and configured
- [ ] Initial migration created from current schema
- [ ] Migration commands documented
- [ ] Auto-run migrations on API startup (optional)

**Success Metric**: Can add a column without dropping tables

---

#### Story NEW-5: Add Container Resource Limits
**Epic**: 2 (Single Script Execution)
**Priority**: Critical
**Estimate**: 1.5 hours

**Why**: Prevent runaway containers from exhausting host resources.

**Acceptance Criteria**:
- [ ] Memory limit: 512MB per container
- [ ] CPU limit: 1 core per container
- [ ] Timeout: 300 seconds (5 minutes) default
- [ ] Configurable via environment/config

**Success Metric**: Container killed when exceeding limits

---

#### Story NEW-6: Implement Job Timeout Mechanism
**Epic**: 8 (Observability)
**Priority**: Critical
**Estimate**: 2 hours

**Why**: Jobs can hang forever if container doesn't exit.

**Acceptance Criteria**:
- [ ] Default timeout: 300 seconds (configurable)
- [ ] Worker enforces timeout
- [ ] Job marked as "failed" with timeout message
- [ ] Timeout visible in status command

**Success Metric**: Long-running script killed after 5 minutes

---

#### Story NEW-7: Dead Worker Detection
**Epic**: 8 (Observability)
**Priority**: High
**Estimate**: 2 hours

**Why**: If worker crashes, jobs stay "running" forever.

**Acceptance Criteria**:
- [ ] Worker sends heartbeat every 30 seconds
- [ ] Heartbeat stored in database
- [ ] Separate cleanup process checks for stale workers
- [ ] Jobs from dead workers marked as "failed"

**Success Metric**: Killed worker's jobs marked failed within 2 minutes

---

### Developer Experience (SHOULD HAVE)

#### Story 2-3: Pre-configured Runtimes
**Epic**: 2 (Single Script Execution)
**Priority**: High
**Estimate**: 2 hours

**Why**: Users shouldn't need to know Docker image names.

**Acceptance Criteria**:
- [ ] Default runtime: python:3.11 (if not specified)
- [ ] Support short names: "python3.11", "python3.12", "node20"
- [ ] Map short names to Docker images
- [ ] Show available runtimes in help text

**Success Metric**: `rgrid run script.py` works without --runtime flag

---

#### Story 2-4: Auto-detect Python Dependencies
**Epic**: 2 (Single Script Execution)
**Priority**: Medium
**Estimate**: 3 hours

**Why**: Users shouldn't need to pre-install deps manually.

**Acceptance Criteria**:
- [ ] Detect requirements.txt in script directory
- [ ] Parse requirements.txt
- [ ] Run pip install before script execution
- [ ] Cache installed packages (optional for Tier 3)

**Success Metric**: Script with requirements.txt runs without manual setup

---

#### Story 10-4: Better Error Messages
**Epic**: 10 (Web Interfaces & MVP Polish)
**Priority**: High
**Estimate**: 2 hours

**Why**: Generic errors don't help users debug.

**Acceptance Criteria**:
- [ ] Structured error types (ValidationError, ExecutionError, etc.)
- [ ] Actionable error messages with suggestions
- [ ] Show relevant context (script name, line number if applicable)
- [ ] Friendly formatting in CLI

**Success Metric**: User can debug issue from error message alone

---

### Nice-to-Have (TIME PERMITTING)

#### Story NEW-8: Separate Stderr Capture
**Epic**: 2 (Single Script Execution)
**Priority**: Low
**Estimate**: 1 hour

**Why**: Currently stderr merged with stdout.

**Acceptance Criteria**:
- [ ] DockerExecutor captures stderr separately
- [ ] Both streams stored in database
- [ ] `rgrid logs --stderr-only` shows only stderr

---

#### Story NEW-9: Worker Startup Script
**Epic**: Infrastructure
**Priority**: Low
**Estimate**: 1 hour

**Why**: Currently manual startup with environment variables.

**Acceptance Criteria**:
- [ ] Script: `scripts/start-worker.sh`
- [ ] Reads DATABASE_URL from .env or environment
- [ ] Validates requirements before starting
- [ ] Runs worker in foreground (for Docker/systemd)

---

## Scope Boundaries

### IN SCOPE (Tier 3)
- ✅ Database migrations
- ✅ Resource limits and timeouts
- ✅ Dead worker detection
- ✅ Pre-configured runtimes
- ✅ Dependency auto-detection
- ✅ Better error messages

### OUT OF SCOPE (Defer to Post-MVP)
- ❌ WebSocket streaming (Epic 8, Story 8-3)
- ❌ Input file handling (Epic 2, Story 2-5)
- ❌ Output files to MinIO (Epic 7, Story 7-2/7-3)
- ❌ Batch execution (Epic 5)
- ❌ Hetzner provisioning (Epic 4)
- ❌ Ray orchestration (Epic 3)
- ❌ Cost tracking (Epic 9)
- ❌ Web console (Epic 10)

## Success Criteria

### Definition of "Production-Ready MVP"

**Reliability**:
- ✅ No manual schema changes required
- ✅ Containers can't exhaust host resources
- ✅ Jobs don't hang forever
- ✅ Worker crashes don't lose jobs

**Usability**:
- ✅ Works without configuration (sensible defaults)
- ✅ Error messages guide users to solutions
- ✅ Common workflows "just work" (requirements.txt, default runtime)

**Operations**:
- ✅ Safe to run migrations without downtime
- ✅ Workers can restart without losing jobs
- ✅ Logs provide enough info for debugging

## Test Plan

### Test 1: Database Migration
```bash
# Add a new column via migration
alembic revision --autogenerate -m "add user_id column"
alembic upgrade head
# Verify: Column exists, data intact
```

### Test 2: Resource Limits
```python
# Script that tries to use 2GB RAM
import numpy as np
big_array = np.zeros((256, 1024, 1024))  # 256MB * 4 iterations
```
**Expected**: Killed after exceeding 512MB

### Test 3: Job Timeout
```python
# Script that runs for 10 minutes
import time
time.sleep(600)
```
**Expected**: Killed after 5 minutes, status shows timeout

### Test 4: Dead Worker Detection
```bash
# Start worker, run job, kill worker process
kill -9 <worker-pid>
# Wait 2 minutes, check status
```
**Expected**: Job marked as failed with "worker died" message

### Test 5: Pre-configured Runtime
```bash
rgrid run hello.py  # No --runtime flag
```
**Expected**: Uses python:3.11 by default

### Test 6: Auto-detect Dependencies
```bash
# Create requirements.txt with requests
echo "requests==2.31.0" > requirements.txt
# Script that imports requests
rgrid run script_using_requests.py
```
**Expected**: Dependencies installed, script succeeds

### Test 7: Better Error Messages
```bash
# Submit invalid script
rgrid run nonexistent.py
```
**Expected**: Clear message like "File not found: nonexistent.py. Check the path and try again."

## Estimates

| Story | Priority | Estimate | Type |
|-------|----------|----------|------|
| NEW-3: Alembic | Critical | 2h | Infrastructure |
| NEW-5: Resource Limits | Critical | 1.5h | Reliability |
| NEW-6: Job Timeout | Critical | 2h | Reliability |
| NEW-7: Dead Worker Detection | High | 2h | Reliability |
| 2-3: Pre-configured Runtimes | High | 2h | UX |
| 2-4: Auto-detect Dependencies | Medium | 3h | UX |
| 10-4: Better Error Messages | High | 2h | UX |
| NEW-8: Separate Stderr | Low | 1h | Enhancement |
| NEW-9: Worker Startup Script | Low | 1h | Operations |

**Total (High Priority)**: ~13.5 hours
**Total (All Stories)**: ~16.5 hours

## Implementation Strategy

### Phase 1: Reliability Foundation (Critical)
1. NEW-3: Set up Alembic
2. NEW-5: Add resource limits
3. NEW-6: Job timeout mechanism
4. NEW-7: Dead worker detection

### Phase 2: Developer Experience (High Priority)
5. 2-3: Pre-configured runtimes
6. 2-4: Auto-detect dependencies
7. 10-4: Better error messages

### Phase 3: Polish (If Time Permits)
8. NEW-8: Separate stderr
9. NEW-9: Worker startup script

## Definition of Done

- [ ] All critical stories implemented and tested
- [ ] All high-priority stories implemented and tested
- [ ] Comprehensive test report created
- [ ] Sprint status updated
- [ ] Tier 3 retrospective completed
- [ ] System ready for production pilot with real users

## Risks

1. **Alembic complexity**: First time adding migrations, might hit snags
2. **Resource limit testing**: Need to test actual memory exhaustion
3. **Heartbeat overhead**: Additional DB writes every 30s per worker
4. **Dependency detection edge cases**: Many ways to specify Python deps

## Post-Tier 3 Candidates

After Tier 3, consider:
- WebSocket log streaming for real-time feedback
- Batch execution for parallel processing
- Hetzner provisioning for true distributed compute
- Cost tracking and billing
- Web console for non-CLI users

---

**Tier 3 Status**: 🔜 READY TO START
**Target Completion**: 1 session (~4-6 hours autonomous implementation)
**Success Metric**: Production-ready MVP that can handle real workloads safely
