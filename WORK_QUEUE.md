# Self-Service Work Queue (Dependency-Aware)

## Project Status: Backend Complete | Frontend Sprint Active 🚀

**32 stories done | 999+ tests passing | Phase 3 Frontend Complete!**

See `OPUS.md` for strategic completion plan.

---

# 🔥 PHASE 1: COMPLETE BACKEND ✅ DONE

**All backend stories complete!** Moving to Phase 2 Stabilization.

## Available Stories (Ready for Parallel Work)

All backend stories complete - see Completed section.

**All Devs**: Move to **Phase 2 tasks** (Performance Testing, Security Audit - see OPUS.md)

---

# 📋 PHASE 2: STABILIZATION ✅ COMPLETE

**Dev 3 Phase 2 Complete:**
- Created 65 new integration tests (test_cli_workflow.py + test_failure_scenarios.py)
- Test coverage: 888 tests total (was 736)
- CLI workflow tests: run -> status -> logs -> cost -> retry
- Failure scenario tests: network, auth, validation, edge cases

**Dev 2 Phase 2 Complete:**
- Security audit completed - 6 vulnerabilities found and fixed
- Fixed CRITICAL: Dockerfile injection via runtime passthrough
- Fixed HIGH: Path traversal in runner file_handler.py
- Fixed HIGH: Symlink attack in output_collector.py
- Fixed HIGH: Path traversal in CLI downloads
- Fixed MEDIUM: Config directory permissions (0700/0600)
- Added 24 security tests (tests/unit/test_security.py)
- Test coverage: 905 tests total (was 851)
- Full report: `docs/SECURITY_AUDIT_REPORT.md`

**Dev 1 Phase 2 Complete:**
- Performance testing framework created (30 tests)
- All OPUS.md targets MET or EXCEEDED:
  - API response: < 2s target, actual 65-90ms (10x faster)
  - CLI response: < 500ms target, actual 41-65ms (10x faster)
  - 100 concurrent requests: 100% success rate, 25.7 req/s
  - Sustained load: Only 13% degradation (50% threshold)
  - Burst recovery: < 1 second
- Tests: tests/performance/ (30 new tests)
- Full report: `docs/PHASE2_PERFORMANCE_REPORT.md`

**Phase 2 Summary:**
- Total tests: 942 passing
- Security vulnerabilities: 6 found, 6 fixed
- Performance: All targets exceeded
- Integration: Full CLI workflow covered

---

# 🎨 PHASE 3: FRONTEND SPRINT (NOW ACTIVE)

**Backend and Stabilization complete! Frontend stories now available.**

---

## Tier 12 - Console (Next.js)

**Goal:** Web console for execution management

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **10-1** | Marketing website landing page | None | `docs/sprint-artifacts/stories/10-1-build-marketing-website-landing-page.md` |
| [DONE] | **10-2** | Console dashboard with history | 10-1 | `docs/sprint-artifacts/stories/10-2-build-console-dashboard-with-execution-history.md` |
| [DONE] | **10-3** | Download outputs via console | 10-2 | `docs/sprint-artifacts/stories/10-3-implement-download-outputs-via-console.md` |

**Frontend Tech Stack:**
- Next.js 14 with App Router
- shadcn/ui for components
- Tailwind CSS for styling
- TypeScript for type safety

---

# 🧪 PHASE 4: STAGING VALIDATION & POLISH (Available for Dev 1)

**Thorough staging testing and polish. NO production deployment yet - focus on quality.**

## Available Tasks (Can start immediately)

| Status | Story | Description | Priority | Effort |
|--------|-------|-------------|----------|--------|
| [DONE] | **STAGE-1** | Staging environment smoke tests | HIGH | 3h |
| [DONE] | **STAGE-2** | End-to-end workflow validation | HIGH | 4h |
| [ ] | **STAGE-3** | API documentation (test on staging) | HIGH | 3h |
| [ ] | **STAGE-4** | Staging stress testing (100+ jobs) | HIGH | 4h |
| [ ] | **STAGE-5** | CLI error handling improvements | MEDIUM | 2h |
| [ ] | **STAGE-6** | Edge case testing & documentation | HIGH | 3h |
| [ ] | **STAGE-7** | Staging monitoring setup | MEDIUM | 3h |
| [ ] | **STAGE-8** | User acceptance test scenarios | HIGH | 2h |
| [ ] | **STAGE-9** | Performance baseline on staging | MEDIUM | 3h |
| [ ] | **STAGE-10** | Data integrity validation | HIGH | 2h |

## Task Descriptions

### STAGE-1: Staging Environment Smoke Tests
- Test all CLI commands against staging.rgrid.dev
- Verify API endpoints are responding
- Check MinIO connectivity and uploads
- Database connection validation
- Create automated smoke test script

### STAGE-2: End-to-End Workflow Validation
- Run complete user journeys on staging
- Test: upload → execute → monitor → download
- Batch processing with 10+ files
- Cost tracking accuracy validation
- Retry and error recovery flows

### STAGE-3: API Documentation (Test on Staging)
- Generate OpenAPI spec from staging API
- Deploy interactive docs
- Test all example requests
- Verify auth flows work correctly
- Document any staging-specific configs

### STAGE-4: Staging Stress Testing (100+ Jobs)
- Submit 100+ concurrent jobs to staging
- Monitor queue handling and worker scaling
- Test database under load
- MinIO bandwidth testing
- Document breaking points and limits

### STAGE-5: CLI Error Handling Improvements
- Test all failure scenarios on staging
- Improve error messages based on findings
- Add helpful recovery suggestions
- Test network interruption handling
- Validate timeout behaviors

### STAGE-6: Edge Case Testing & Documentation
- Document all edge cases discovered
- Test with invalid/malformed inputs
- Large file handling (>1GB)
- Unicode and special characters
- Create edge case test suite

### STAGE-7: Staging Monitoring Setup
- Set up basic Grafana for staging
- Create dashboards for key metrics
- Queue depth and worker status
- Performance metrics tracking
- Alert on staging failures

### STAGE-8: User Acceptance Test Scenarios
- Write UAT test scripts
- Cover top 10 use cases
- Document expected vs actual
- Performance benchmarks
- Create test data sets

### STAGE-9: Performance Baseline on Staging
- Measure performance of all operations
- Create baseline metrics document
- Identify slow queries or operations
- Memory and CPU profiling
- Network latency measurements

### STAGE-10: Data Integrity Validation
- Verify no data loss in workflows
- Test concurrent access patterns
- Validate cost calculations
- Check file integrity after transfer
- Database consistency checks

---

## Completed

| Story | Description | Agent | Wave |
|-------|-------------|-------|------|
| [DONE] **STAGE-1** | Staging environment smoke tests | Dev 1 | Phase 4 |
| [DONE] **10-3** | Download outputs via console | Dev 3 | Phase 3 |
| [DONE] **10-2** | Console dashboard with history | Dev 2 | Phase 3 |
| [DONE] **10-1** | Marketing website landing page | Dev 1 | Phase 3 |
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
| [DONE] **10-5** | Network failure graceful handling | Dev 2 | 12 |
| [DONE] **10-8** | Execution metadata tagging | Dev 3 | 12 |
| [DONE] **6-3** | Automatic cache invalidation | Dev 3 | 12 |
| [DONE] **6-4** | Optional input file caching | Dev 1 | 13 |
| [DONE] **9-5** | Cost alerts (threshold notifications) | Dev 2 | 13 |

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

## BMAD-Optimized Agent Prompt

```
You are an autonomous dev agent with specialized expertise. Complete ONE story per session, then stop.

AGENT SPECIALIZATIONS:
- Dev 1: "Backend Specialist" - Cache systems, performance, file handling
- Dev 2: "Full-Stack Bridge" - API integration, alerts, monitoring
- Dev 3: "Quality Guardian" - Testing, security, documentation

WORKFLOW:
1. Read WORK_QUEUE.md - check PHASE 1 section for available stories
2. Find a [ ] story matching your specialization (or any if yours unavailable)
3. Claim it: edit WORK_QUEUE.md, change [ ] to [IN PROGRESS: Dev N]
4. Read full story file from docs/sprint-artifacts/stories/
5. Implement with TDD:
   - Write failing tests FIRST (red phase)
   - Implement minimal code to pass (green phase)
   - Refactor if needed (refactor phase)
6. Run tests: venv/bin/pytest tests/ -v
7. Verify on staging: export RGRID_API_URL=https://staging.rgrid.dev/api/v1/
8. Commit with descriptive message and push to main
9. Edit WORK_QUEUE.md: change [IN PROGRESS: Dev N] to [DONE]
10. Move story to Completed section with your Dev number and wave
11. STOP and output: "✅ Story X-Y complete. Run /clear then restart me for next story."

QUALITY STANDARDS:
- Must have unit tests (tests/unit/)
- Must have integration tests if applicable (tests/integration/)
- Must pass all existing tests (736+ tests)
- Must update documentation if API changes

STOP CONDITIONS:
- Story completed successfully → "✅ Story X-Y complete. /clear then restart."
- No stories available → Check Phase 2 tasks in OPUS.md
- Blocked → "⚠️ BLOCKED: <reason>" and stop

COORDINATION:
- Push frequently to avoid conflicts
- Check WORK_QUEUE.md before claiming to avoid collisions
- Leave discoveries in story file comments for other devs

IMPORTANT: Complete ONE story, then STOP for /clear. Quality > Speed.
```
