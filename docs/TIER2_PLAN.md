# Tier 2 Implementation Plan - "Demo-Ready"

**Goal:** Transform the walking skeleton into a functional, demo-ready system that executes scripts automatically and provides observability.

**Target Date:** TBD
**Estimated Effort:** ~2-3 days
**Stories:** 10

---

## Success Criteria for Tier 2

At the end of Tier 2, users should be able to:

1. ✅ Submit a script with `rgrid run script.py`
2. ✅ Script executes **automatically** (no manual intervention)
3. ✅ Check status with `rgrid status <exec_id>`
4. ✅ View output with `rgrid logs <exec_id>`
5. ✅ See scripts transition: queued → running → completed
6. ✅ Handle Python dependencies automatically
7. ✅ Support custom runtimes (python:3.9, python:3.11, etc.)

**Tier 2 is considered COMPLETE when:**
- Epic 2 is 100% done (7/7 stories)
- Worker daemon is running and claiming jobs
- All observability commands work
- Can demo the full flow end-to-end on localhost

---

## Tier 2 Stories (10 Total)

### Phase 1: Core Worker Implementation (Critical)

#### NEW-1: Implement Worker Daemon with Polling Loop
**Epic:** 2 (Single Script Execution)
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 4 hours

**Description:**
Create a worker daemon that continuously polls the database for queued jobs, claims them atomically, executes them in Docker, and updates status.

**Acceptance Criteria:**
- Worker polls `executions` table every 5 seconds
- Claims jobs using `FOR UPDATE SKIP LOCKED` (atomic)
- Updates status: queued → running → completed (or failed)
- Handles multiple concurrent executions (configurable limit)
- Graceful shutdown on SIGTERM
- Logs all activities

**Technical Notes:**
- Use asyncio for polling loop
- SQLAlchemy: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1`
- Call DockerExecutor for actual execution
- Update execution record with timestamps and exit_code

**Files to Create:**
- `runner/runner/worker.py` - Main worker daemon
- `runner/runner/poller.py` - Queue polling logic

**Files to Modify:**
- `api/app/models/execution.py` - May need status_updated_at field

---

#### NEW-2: Add stdout/stderr Storage to Database
**Epic:** 2 (Single Script Execution)
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 2 hours

**Description:**
Add database columns and API support for storing and retrieving script execution output.

**Acceptance Criteria:**
- Database migration adds `stdout` TEXT and `stderr` TEXT columns
- Worker stores output after execution completes
- Output truncated if > 100KB (with warning)
- API returns stdout/stderr in ExecutionResponse
- Empty stderr if no errors

**Technical Notes:**
- Use Alembic for database migration
- Add `output_truncated: bool` field to track truncation
- Set reasonable limits (100KB for demo, configurable later)

**Files to Create:**
- `api/alembic/versions/002_add_output_columns.py` - Migration

**Files to Modify:**
- `api/app/models/execution.py` - Add stdout, stderr, output_truncated fields
- `api/app/schemas/execution.py` - Update ExecutionResponse
- `runner/runner/worker.py` - Store output after execution

---

### Phase 2: Observability Commands (Critical)

#### Story 8-1: Implement `rgrid status` Command
**Epic:** 8 (Observability & Real-time Feedback)
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 2 hours

**Description:**
Allow users to check the status of an execution by ID.

**Acceptance Criteria:**
```bash
$ rgrid status exec_abc123

Execution: exec_abc123
Status: completed
Runtime: python:3.11
Created: 2025-11-15 16:30:00
Started: 2025-11-15 16:30:05
Completed: 2025-11-15 16:30:10
Duration: 5s
Exit Code: 0
```

**Technical Notes:**
- Add `GET /api/v1/executions/{id}` endpoint (if not exists)
- CLI command parses response and formats nicely
- Show duration calculation (completed_at - started_at)
- Handle different statuses (queued, running, completed, failed)

**Files to Create:**
- `cli/rgrid/commands/status.py` - Status command

**Files to Modify:**
- `cli/rgrid/cli.py` - Register status command
- `api/app/api/v1/executions.py` - Ensure GET endpoint exists

---

#### Story 8-2: Implement `rgrid logs` Command
**Epic:** 8 (Observability & Real-time Feedback)
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 2 hours

**Description:**
Allow users to view the stdout/stderr output of an execution.

**Acceptance Criteria:**
```bash
$ rgrid logs exec_abc123

=== STDOUT ===
Hello from RGrid!
Python version: 3.11.14
Result: 42

=== STDERR ===
(empty)

Exit Code: 0
```

**Technical Notes:**
- Reuse GET /api/v1/executions/{id} endpoint
- Extract stdout and stderr from response
- Format nicely with separators
- Handle empty output
- Show warning if output was truncated

**Files to Create:**
- `cli/rgrid/commands/logs.py` - Logs command

**Files to Modify:**
- `cli/rgrid/cli.py` - Register logs command

---

### Phase 3: Complete Epic 2 (Important)

#### Story 2-3: Implement Pre-configured Runtimes
**Epic:** 2 (Single Script Execution)
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 3 hours

**Description:**
Support multiple Python versions via --runtime flag and maintain a list of pre-configured runtimes.

**Acceptance Criteria:**
```bash
$ rgrid run script.py --runtime python:3.9
$ rgrid run script.py --runtime python:3.11
$ rgrid run script.py --runtime python:3.12

$ rgrid runtimes list
python:3.9-slim
python:3.10-slim
python:3.11-slim (default)
python:3.12-slim
```

**Technical Notes:**
- Default to python:3.11-slim
- Validate runtime against allowed list
- Add `rgrid runtimes list` command
- Consider adding node:20, ruby:3.2 later

**Files to Create:**
- `cli/rgrid/commands/runtimes.py` - List runtimes command
- `common/rgrid_common/runtimes.py` - Runtime definitions

**Files to Modify:**
- `cli/rgrid/commands/run.py` - Validate runtime
- `api/app/schemas/execution.py` - Update runtime validation

---

#### Story 2-4: Auto-detect and Install Python Dependencies
**Epic:** 2 (Single Script Execution)
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 4 hours

**Description:**
Automatically detect requirements.txt or imports and install dependencies before execution.

**Acceptance Criteria:**
- If `requirements.txt` in same directory, install deps automatically
- Parse script imports and suggest `pip install` for common packages
- Show dependency installation progress
- Cache installed dependencies (basic - just in container for now)

**Technical Notes:**
- Check for requirements.txt in script directory
- Run `pip install -r requirements.txt` inside container before script
- For now, don't persist dependency layers (Tier 3)
- Add timeout for dependency installation (5 min max)

**Files to Modify:**
- `runner/runner/executor.py` - Add dependency installation step
- `cli/rgrid/commands/run.py` - Upload requirements.txt if exists

---

#### Story 2-5: Handle Script Input Files as Arguments
**Epic:** 2 (Single Script Execution)
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 3 hours

**Description:**
Support passing file paths as script arguments and make them accessible inside the container.

**Acceptance Criteria:**
```bash
$ rgrid run process.py input.txt output.txt

# Inside container, script receives:
# sys.argv[1] = 'input.txt'
# sys.argv[2] = 'output.txt'
# Files are available in /workspace/
```

**Technical Notes:**
- Mount input files into container at /workspace/
- Pass file basenames as arguments to script
- Read-only mounts for input files
- For now, assume files are local (MinIO upload comes later)

**Files to Modify:**
- `runner/runner/executor.py` - Mount additional file volumes
- `cli/rgrid/commands/run.py` - Detect file arguments

---

#### Story 2-7: Support Environment Variables via --env Flag
**Epic:** 2 (Single Script Execution)
**Priority:** 🟢 LOW (already partially done)
**Estimated Effort:** 1 hour

**Description:**
Enhance existing --env flag support (already works, just needs better docs and testing).

**Acceptance Criteria:**
- Multiple --env flags work correctly ✅ (already done)
- Environment variables passed to container ✅ (already done)
- Add validation for env var format (KEY=value)
- Better error messages for malformed env vars

**Technical Notes:**
- This mostly works already from Tier 1
- Just needs validation and better error handling

**Files to Modify:**
- `cli/rgrid/commands/run.py` - Add env var format validation

---

### Phase 4: Infrastructure & Polish (Nice to Have)

#### NEW-3: Add Database Migration Support
**Epic:** 1 (Foundation)
**Priority:** 🟢 LOW
**Estimated Effort:** 2 hours

**Description:**
Set up Alembic for database schema migrations so we can evolve the schema cleanly.

**Acceptance Criteria:**
- Alembic configured in api/ package
- Initial migration captures current schema
- Migration for adding stdout/stderr columns
- Makefile targets for migrations (make migrate, make migrate-upgrade)

**Technical Notes:**
- Install alembic
- Create alembic.ini
- Create migrations directory
- Add auto-generation capability

**Files to Create:**
- `api/alembic.ini` - Alembic config
- `api/alembic/env.py` - Migration environment
- `api/alembic/versions/001_initial.py` - Initial schema

**Files to Modify:**
- `api/pyproject.toml` - Add alembic dependency
- `Makefile` - Add migration targets

---

#### NEW-4: Improve Error Handling and Logging
**Epic:** 2 (Single Script Execution)
**Priority:** 🟢 LOW
**Estimated Effort:** 2 hours

**Description:**
Better error messages, structured logging, and failure handling.

**Acceptance Criteria:**
- Worker logs all errors clearly
- API returns meaningful error messages
- CLI shows helpful error hints
- Failed executions show failure reason
- Timeout handling (max execution time: 10 min)

**Technical Notes:**
- Use structlog for structured logging
- Add execution_error field to store error messages
- Set max_execution_time limit
- Worker kills container after timeout

**Files to Modify:**
- `runner/runner/worker.py` - Better error handling
- `api/app/models/execution.py` - Add execution_error field
- `cli/rgrid/cli.py` - Better error display

---

## Story Sequencing

**Recommended Order:**

1. **NEW-2** - Add stdout/stderr storage (database schema change first)
2. **NEW-3** - Database migrations (infrastructure for schema changes)
3. **NEW-1** - Worker daemon (core functionality)
4. **Story 8-1** - `rgrid status` command
5. **Story 8-2** - `rgrid logs` command
6. **Story 2-3** - Pre-configured runtimes
7. **Story 2-4** - Dependency detection
8. **Story 2-5** - Input file handling
9. **Story 2-7** - Env var enhancement
10. **NEW-4** - Error handling polish

**Rationale:**
- Database schema changes first (migrations framework + new columns)
- Then worker (depends on schema changes)
- Then observability commands (depend on worker)
- Then complete Epic 2 enhancements
- Finally polish

---

## Definition of Done (Tier 2)

### Technical Completion:
- [ ] All 10 stories implemented
- [ ] Worker daemon running and claiming jobs
- [ ] Scripts execute automatically
- [ ] Status transitions work (queued → running → completed)
- [ ] stdout/stderr captured and stored
- [ ] `rgrid status` and `rgrid logs` commands work
- [ ] Tests passing (unit + integration)

### User Experience:
- [ ] Can submit script with `rgrid run`
- [ ] Can check status with `rgrid status`
- [ ] Can view logs with `rgrid logs`
- [ ] Executions complete in <30 seconds for simple scripts
- [ ] Error messages are clear and actionable

### Documentation:
- [ ] TIER2_TEST_REPORT.md created
- [ ] Updated README with Tier 2 features
- [ ] Worker daemon usage documented

### Deployment:
- [ ] Worker can run as background process
- [ ] Docker containers clean up after execution
- [ ] No resource leaks

---

## Out of Scope for Tier 2

These are explicitly **NOT** in Tier 2:

- ❌ Ray cluster integration (Tier 3)
- ❌ Hetzner cloud provisioning (Tier 3)
- ❌ Batch execution (Tier 3)
- ❌ Content-hash caching (Tier 3)
- ❌ Real-time WebSocket streaming (Tier 3)
- ❌ Clerk authentication (Tier 3)
- ❌ Multi-tenancy (Tier 3)
- ❌ MinIO file uploads (can defer)
- ❌ Cost tracking (Tier 3)

**Why?** Tier 2 focuses on making the single-machine experience solid before adding complexity.

---

## Risks and Mitigations

### Risk 1: Worker Complexity
**Mitigation:** Start simple, add features incrementally

### Risk 2: Database Locking Issues
**Mitigation:** Test with multiple workers locally, use proven pattern

### Risk 3: Output Size Limits
**Mitigation:** Set clear limits, truncate with warning

---

## Success Metrics

**Tier 2 is successful if:**
- Can demo full flow in <5 minutes
- No manual database queries needed
- Works reliably on localhost
- Foundation ready for Tier 3 scaling

---

**Prepared by:** Claude (BMad Method)
**Date:** 2025-11-15
**Status:** Ready for implementation
