# Self-Service Work Queue (Dependency-Aware)

## How It Works

Stories are grouped by tier. Only claim stories whose dependencies are marked [DONE].

---

# ✅ STABILIZATION GATE COMPLETE

**26 stories validated. 652 tests passing. Ready for next sprint!**

See: `docs/TIER5_8_VALIDATION_REPORT.md` for full validation details.

---

# REMAINING BACKLOG

## Tier 9 - CLI Polish & Resilience (All can start NOW)

**Goal:** Improve CLI robustness and batch retry capabilities

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **5-6** | Retry failed batch executions | 5-5 ✅ | `docs/sprint-artifacts/stories/5-6-implement-retry-for-failed-batch-executions.md` |
| [IN PROGRESS: Dev 2] | **10-5** | Network failure graceful handling | None | `docs/sprint-artifacts/stories/10-5-implement-network-failure-graceful-handling.md` |
| [IN PROGRESS: Dev 3] | **10-8** | Execution metadata tagging | None | `docs/sprint-artifacts/stories/10-8-implement-execution-metadata-tagging.md` |

---

## Tier 10 - Advanced Caching (After Tier 9 or parallel)

**Goal:** Complete caching story with invalidation and input file caching

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [ ] | **6-3** | Automatic cache invalidation | 6-2 ✅ | `docs/sprint-artifacts/stories/6-3-implement-automatic-cache-invalidation.md` |
| [ ] | **6-4** | Optional input file caching | 6-1 ✅ | `docs/sprint-artifacts/stories/6-4-implement-optional-input-file-caching.md` |

---

## Tier 11 - Future Enhancements

**Goal:** Cost alerting and future features

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [ ] | **9-5** | Cost alerts (future) | 9-1 ✅ | `docs/sprint-artifacts/stories/9-5-implement-cost-alerts-future-enhancement.md` |

---

## Tier 12 - Console (Next.js - SEPARATE SPRINT)

**Goal:** Web console for execution management - requires frontend expertise

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [BLOCKED] | **10-1** | Marketing website landing page | None | `docs/sprint-artifacts/stories/10-1-build-marketing-website-landing-page.md` |
| [BLOCKED] | **10-2** | Console dashboard with history | 10-1 | `docs/sprint-artifacts/stories/10-2-build-console-dashboard-with-execution-history.md` |
| [BLOCKED] | **10-3** | Download outputs via console | 10-2 | `docs/sprint-artifacts/stories/10-3-implement-download-outputs-via-console.md` |

**Note:** Console stories marked BLOCKED pending frontend sprint planning.

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
| [DONE] **5-6** | Retry failed batch executions | Dev 1 | 12 |

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
You are an autonomous dev agent. Complete ONE story per session, then stop.

1. Read WORK_QUEUE.md
2. Find a [ ] story whose dependencies are all [DONE] or ✅
3. Claim it: edit WORK_QUEUE.md, change [ ] to [IN PROGRESS: Dev N]
4. Read full story file from docs/sprint-artifacts/stories/
5. Implement with TDD (write tests first)
6. Run tests: venv/bin/pytest tests/ -v
7. Commit and merge to main
8. Edit WORK_QUEUE.md: change [IN PROGRESS: Dev N] to [DONE]
9. Check if any [BLOCKED] stories can now be [ ] (deps met)
10. STOP and output: "Story X-Y complete. Run /clear then restart me for next story."

STOP CONDITIONS:
- Story completed successfully → output completion message
- No [ ] stories available → output "Queue empty or all blocked"
- Error/blocker encountered → output "BLOCKED: <reason>" and stop

IMPORTANT: Do NOT loop. Complete ONE story, then STOP so user can /clear context.
```
