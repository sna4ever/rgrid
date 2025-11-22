# Self-Service Work Queue (Dependency-Aware)

## How It Works

Stories are grouped by tier. Only claim stories whose dependencies are marked [DONE].

---

# 🚨 STABILIZATION GATE - MUST COMPLETE BEFORE NEW FEATURES 🚨

**26 stories completed without deployment verification. Stabilize first!**

## Phase 1: Parallel Fixes (All 3 agents can start NOW)

| Status | Task | Description | Depends On |
|--------|------|-------------|------------|
| [DONE] | **STAB-1** | Fix 7 failing tests | None |
| [DONE] | **STAB-2** | Audit & generate missing DB migrations | None |
| [DONE] | **STAB-3** | Review new API endpoints for deployment | None |

## Phase 2: Deployment (After Phase 1 complete)

| Status | Task | Description | Depends On |
|--------|------|-------------|------------|
| [DONE] | **STAB-4** | Apply migrations & deploy to staging | STAB-1 ✅, STAB-2 ✅, STAB-3 ✅ |

## Phase 3: Validation (After deployment)

| Status | Task | Description | Depends On |
|--------|------|-------------|------------|
| [ ] | **STAB-5** | E2E smoke test all new features | STAB-4 ✅ |
| [ ] | **STAB-6** | Write E2E tests for new CLI commands | STAB-4 ✅ |
| [BLOCKED] | **STAB-7** | Create TIER5_VALIDATION_REPORT.md | STAB-5, STAB-6 |

---

### STAB-1: Fix Failing Tests

**7 tests currently failing:**
```
tests/deployment/test_alembic_readiness.py::test_alembic_ini_exists
tests/deployment/test_alembic_readiness.py::test_migration_includes_expected_tables
tests/deployment/test_environment_validation.py::test_systemd_uses_correct_module_path
tests/integration/test_end_to_end.py::test_api_create_execution
tests/integration/test_end_to_end.py::test_api_accepts_valid_key
tests/unit/test_docker_image_prepull.py::test_cloud_init_prepull_before_ray_start
tests/unit/test_docker_image_prepull.py::test_custom_images_are_commented_out
```

**Steps:**
1. Run `venv/bin/pytest tests/ -v --tb=short 2>&1 | grep FAILED`
2. Fix each test or mark as skip with reason
3. Target: 0 failures

**Done when:** `venv/bin/pytest tests/` shows 0 failures

---

### STAB-2: Audit Database Migrations

**Stories that likely need DB changes:**
- 8-6: Track execution metadata → new columns
- 9-1/9-2: Cost tracking → cost_microns column
- 6-1/6-2: Caching → script_hash column

**Steps:**
1. Check `api/api/models/` for new fields
2. Compare against `api/alembic/versions/`
3. Generate: `cd api && alembic revision --autogenerate -m "Tier 5-8 schema updates"`
4. Review and commit migration

**Done when:** All model changes have migrations

---

### STAB-3: Review API Endpoints

**New endpoints to verify:**
- `GET /executions/{id}/status` (8-1)
- `GET /executions/{id}/logs` (8-2)
- `WS /executions/{id}/logs/stream` (8-3)
- `GET /executions/{id}/cost` (9-3)
- `POST /executions/{id}/retry` (10-6)

**Steps:**
1. List all new routers in `api/api/endpoints/`
2. Verify registered in `api/api/main.py`
3. Document endpoint list for deployment

**Done when:** All endpoints documented, routers verified

---

### STAB-4: Deploy to Staging

**Requires:** STAB-1, STAB-2, STAB-3 all [DONE]

**Steps:**
```bash
ssh deploy@46.62.246.120
cd /home/deploy/rgrid && git pull
source .env.staging
cd api && alembic upgrade head
sudo systemctl restart api-staging orchestrator-staging runner-staging
curl https://staging.rgrid.dev/api/v1/health
```

**Done when:** Health check returns 200

---

### STAB-5: E2E Smoke Tests

**Test each feature on staging:**
```bash
# Configure CLI for staging
export RGRID_API_URL=https://staging.rgrid.dev/api/v1

# Test batch
rgrid run script.py --batch "*.csv" --parallel 3

# Test download
rgrid run script.py input.csv  # verify outputs download

# Test status/logs/cost
rgrid status <exec_id>
rgrid logs <exec_id>
rgrid cost <exec_id>

# Test retry
rgrid retry <failed_exec_id>
```

**Done when:** All commands work correctly

---

### STAB-6: Write E2E Tests

**Create tests in `tests/e2e/`:**
- `test_batch_workflow.py`
- `test_download_workflow.py`
- `test_monitoring_commands.py`
- `test_cost_tracking.py`

**Done when:** Tests pass against staging

---

### STAB-7: Validation Report

**Create `docs/TIER5_8_VALIDATION_REPORT.md`:**
- Stories completed (26)
- Test results summary
- Deployment verification
- Performance observations
- Known issues / bugs found

**Done when:** Report committed to main

---

## Completed

| Story | Description | Agent | Wave |
|-------|-------------|-------|------|
| [DONE] **BUG-1** | Fix executor return value | Dev 1 | 1 |
| [DONE] **5-1** | Batch flag with glob | Dev 2 | 1 |
| [DONE] **7-3** | MinIO retention policy | Dev 3 | 1 |
| [DONE] **5-2** | Parallel flag | Dev 1 | 2 |
| [DONE] **7-1** | Auto-upload input files | Dev 2 | 2 |
| [DONE] **7-4** | Auto-download outputs | Dev 3 | 3 |
| [DONE] **5-3** | Batch progress tracking | Dev 1 | 4 |
| [DONE] **5-4** | Organize batch outputs | Dev 2 | 4 |
| [DONE] **5-5** | Handle batch failures | Dev 3 | 4 |
| [DONE] **2-4** | Auto-detect Python deps | Dev 1 | 5 |
| [DONE] **7-5** | Remote-only flag (skip download) | Dev 3 | 5 |
| [DONE] **6-1** | Script content hashing | Dev 2 | 5 |
| [DONE] **8-1** | rgrid status command | Dev 1 | 6 |
| [DONE] **7-6** | Large file streaming | Dev 3 | 6 |
| [DONE] **8-2** | rgrid logs command | Dev 1 | 7 |
| [DONE] **6-2** | Dependency layer caching | Dev 2 | 7 |
| [DONE] **9-1** | MICRONS cost calculation | Dev 1 | 8 |
| [DONE] **8-6** | Track execution metadata | Dev 3 | 8 |
| [DONE] **8-3** | WebSocket log streaming | Dev 2 | 8 |
| [DONE] **8-4** | CLI reconnection for WebSocket | Dev 2 | 9 |
| [DONE] **9-2** | Billing hour cost amortization | Dev 1 | 9 |
| [DONE] **9-3** | rgrid cost command | Dev 3 | 9 |
| [DONE] **9-4** | Cost estimation for batches | Dev 3 | 10 |
| [DONE] **8-5** | Batch progress with --watch | Dev 2 | 10 |
| [DONE] **10-7** | Auto-retry transient failures | Dev 1 | 11 |

---

## Tier 4.5 - Batch Execution ✅ COMPLETE

**Goal**: Complete batch execution capability - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **5-2** | Parallel flag | 5-1 [DONE] | `queue/next-5-2-parallel-flag.md` |

---

## Tier 5 Phase 1-2 - File Management ✅ COMPLETE

**Goal**: Seamless file upload/download - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **7-1** | Auto-upload input files | None | `queue/next-7-1-auto-upload.md` |
| [DONE] | **7-4** | Auto-download outputs | 7-3 [DONE] | `queue/next-7-4-auto-download.md` |

---

## Tier 5 Phase 3 - Batch Management ✅ COMPLETE

**Goal**: Batch progress, outputs, and failure handling - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **5-3** | Batch progress tracking | 5-1 ✅, 5-2 ✅ | `docs/sprint-artifacts/stories/5-3-track-batch-execution-progress.md` |
| [DONE] | **5-4** | Organize batch outputs | 5-1 ✅ | `docs/sprint-artifacts/stories/5-4-organize-batch-outputs-by-input-filename.md` |
| [DONE] | **5-5** | Handle batch failures | 5-1 ✅ | `docs/sprint-artifacts/stories/5-5-handle-batch-failures-gracefully.md` |

---

## Tier 5 Phase 4 - Dependencies ✅ COMPLETE

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **2-4** | Auto-detect Python deps | None | `docs/sprint-artifacts/stories/2-4-auto-detect-and-install-python-dependencies.md` |

---

## Tier 5 Phase 5 - Caching ✅ COMPLETE

**Goal**: Script and dependency caching for instant repeat executions - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **6-1** | Script content hashing | 7-1 ✅ | `docs/sprint-artifacts/stories/6-1-implement-script-content-hashing-and-cache-lookup.md` |
| [DONE] | **6-2** | Dependency layer caching | 6-1 ✅ | `docs/sprint-artifacts/stories/6-2-implement-dependency-layer-caching.md` |

---

## Tier 5 Phase 6 - Advanced File Management ✅ COMPLETE

**Goal**: Large file handling with streaming and compression - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **7-5** | Remote-only flag (skip download) | 7-4 ✅ | `docs/sprint-artifacts/stories/7-5-implement-remote-only-flag-to-skip-auto-download.md` |
| [DONE] | **7-6** | Large file streaming | 7-5 ✅ | `docs/sprint-artifacts/stories/7-6-implement-large-file-streaming-and-compression.md` |

---

## Tier 6 - Monitoring & UX (Epic 8) ✅ COMPLETE

**Goal**: Full observability with status, logs, and progress monitoring - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **8-1** | rgrid status command | Epic 2 ✅ | `docs/sprint-artifacts/stories/8-1-implement-rgrid-status-command.md` |
| [DONE] | **8-2** | rgrid logs command | Epic 2 ✅ | `docs/sprint-artifacts/stories/8-2-implement-rgrid-logs-command-with-historical-logs.md` |
| [DONE] | **8-3** | WebSocket log streaming | 8-2 ✅ | `docs/sprint-artifacts/stories/8-3-implement-websocket-log-streaming-for-real-time-logs.md` |
| [DONE] | **8-4** | CLI reconnection for WebSocket | 8-3 ✅ | `docs/sprint-artifacts/stories/8-4-implement-cli-reconnection-for-websocket-streams.md` |
| [DONE] | **8-5** | Batch progress with --watch | 5-3 ✅, 8-3 ✅ | `docs/sprint-artifacts/stories/8-5-implement-batch-progress-display-with-watch.md` |
| [DONE] | **8-6** | Track execution metadata | Epic 2 ✅ | `docs/sprint-artifacts/stories/8-6-track-execution-metadata-in-database.md` |

---

## Tier 7 - Cost Tracking (Epic 9) ✅ COMPLETE

**Goal**: Transparent, predictable cost tracking with per-execution granularity - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **9-1** | MICRONS cost calculation | Epic 4 ✅ | `docs/sprint-artifacts/stories/9-1-implement-microns-cost-calculation.md` |
| [DONE] | **9-2** | Billing hour cost amortization | 9-1 ✅ | `docs/sprint-artifacts/stories/9-2-implement-billing-hour-cost-amortization.md` |
| [DONE] | **9-3** | rgrid cost command | 9-1 ✅ | `docs/sprint-artifacts/stories/9-3-implement-rgrid-cost-command.md` |
| [DONE] | **9-4** | Cost estimation for batches | 9-1 ✅ | `docs/sprint-artifacts/stories/9-4-implement-cost-estimation-for-batch-executions.md` |

---

## Tier 8 - Error Handling & Retry (Epic 10 partial)

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **10-4** | Structured error handling | Epic 2 ✅ | `docs/sprint-artifacts/stories/10-4-implement-structured-error-handling-with-clear-messages.md` |
| [DONE] | **10-6** | Manual retry command | Epic 2 ✅ | `docs/sprint-artifacts/stories/10-6-implement-manual-retry-command.md` |
| [DONE] | **10-7** | Auto-retry transient failures | 10-6 ✅ | `docs/sprint-artifacts/stories/10-7-implement-auto-retry-for-transient-failures.md` |

---

## Claiming Rules

1. **Only claim [ ] stories** (not [BLOCKED] or [DONE])
2. **Check "Depends On" column** - all deps must be [DONE]
3. **Edit this file** to change [ ] → [CLAIMING: Dev X]
4. **Work on story** using TDD, merge to main
5. **Mark [DONE]** when merged
6. **Unblock dependent stories** by changing [BLOCKED] → [ ] if deps now met

---

## Quick Start for Agents

**Just run this prompt:**
```
Read WORK_QUEUE.md and follow the Agent Prompt. You are Dev [1/2/3].
```

---

## Agent Prompt

```
You are an autonomous dev agent. Complete ONE task per session, then stop.

PRIORITY: Complete STAB-* tasks first (Stabilization Gate). Only do regular stories after all STAB tasks are [DONE].

1. Read WORK_QUEUE.md
2. Find a [ ] task (STAB-* or story) whose dependencies are all [DONE] or ✅
3. Claim it: edit WORK_QUEUE.md, change [ ] to [IN PROGRESS: Dev N]
4. For STAB tasks: follow instructions in the task section below
   For stories: read file from docs/sprint-artifacts/stories/
5. Complete the task (fix tests, generate migrations, review endpoints, etc.)
6. Commit changes to main
7. Edit WORK_QUEUE.md: change [IN PROGRESS: Dev N] to [DONE]
8. Check if any [BLOCKED] tasks can now be [ ] (deps met)
9. STOP and output: "Task STAB-X complete. Run /clear then restart me."

STOP CONDITIONS:
- Task completed successfully → output completion message
- No [ ] tasks available → output "Queue empty or all blocked"
- Error/blocker encountered → output "BLOCKED: <reason>" and stop

IMPORTANT: Do NOT loop. Complete ONE task, then STOP so user can /clear context.
```
