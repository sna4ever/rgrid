# Tier 4 Plan: Distributed Execution & Cloud Infrastructure

**Date**: 2025-11-15
**Status**: PLANNING
**Focus**: Enable horizontal scaling and elastic compute

## Tier Overview

Tier 4 transforms RGrid from a single-node execution system to a fully distributed, auto-scaling cloud platform. This tier implements Ray cluster orchestration, Hetzner worker provisioning, and complete file handling - unlocking horizontal scaling and elastic infrastructure.

**Key Objectives**:
1. Enable distributed job execution across multiple workers via Ray cluster
2. Implement automatic Hetzner worker provisioning and lifecycle management
3. Complete MinIO file upload/download workflow
4. Establish production-grade worker health monitoring and auto-replacement

**Expected Outcome**: RGrid can distribute jobs across 3+ auto-provisioned Hetzner workers, automatically scaling based on queue depth, with reliable failure detection and worker replacement. Files upload/download correctly across distributed execution.

---

## Stories Included

### Phase 1: File Handling Foundation

#### Story 2-5: Handle Script Input Files as Arguments
**Epic**: Epic 2 - Single Script Execution
**Priority**: Critical
**Estimate**: 4-6 hours
**Complexity**: Medium
**Risk**: Low

**Why**: File handling must work before distributing jobs across nodes. Without this, scripts cannot receive input data in distributed execution.

**Acceptance Criteria**:
- [ ] CLI detects file arguments by checking os.path.exists()
- [ ] CLI uploads files to MinIO (executions/<exec_id>/inputs/)
- [ ] MinIO presigned PUT URLs used for uploads
- [ ] Runner downloads files into container /work directory before execution
- [ ] Runner passes /work/filename as argument to script
- [ ] Script can read files normally (identical to local execution)
- [ ] Handles multiple input files correctly
- [ ] Upload files >10MB successfully

**Success Metric**: Script receives file path and can read 10MB+ input file identically to local execution

**Story File**: `docs/sprint-artifacts/stories/2-5-handle-input-files.md`

---

### Phase 2: Ray Cluster Setup

#### Story 3-1: Set Up Ray Head Node on Control Plane
**Epic**: Epic 3 - Distributed Orchestration
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Medium (Ray cluster networking)

**Why**: Foundation for distributed task scheduling. Ray head node coordinates all distributed execution.

**Acceptance Criteria**:
- [ ] Ray head node runs as separate container on control plane
- [ ] Ray serves on port 6379 (Redis protocol)
- [ ] Ray dashboard available on port 8265
- [ ] Workers can connect via private IP (10.0.0.1:6379)
- [ ] Ray head node visible in dashboard
- [ ] Connection test from localhost successful

**Success Metric**: Ray dashboard accessible at http://localhost:8265, workers can connect

**Story File**: `docs/sprint-artifacts/stories/3-1-ray-head-node.md`

---

#### Story 3-2: Initialize Ray Worker on Each Hetzner Node
**Epic**: Epic 3 - Distributed Orchestration
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Medium (cloud-init timing issues)

**Why**: Workers must join Ray cluster to receive task assignments.

**Acceptance Criteria**:
- [ ] Cloud-init script starts Ray worker on boot
- [ ] Ray worker connects to head node at 10.0.0.1:6379
- [ ] Ray worker registers with cluster within 60 seconds
- [ ] Worker visible in Ray dashboard
- [ ] Worker advertises max_concurrent = 2 (1 job per vCPU for CX22)
- [ ] Worker resources: 2 CPUs, 4GB RAM

**Success Metric**: Worker appears in Ray dashboard and accepts tasks

**Story File**: `docs/sprint-artifacts/stories/3-2-ray-worker-init.md`

---

### Phase 3: Ray Task Distribution

#### Story 3-3: Submit Executions as Ray Tasks
**Epic**: Epic 3 - Distributed Orchestration
**Priority**: Critical
**Estimate**: 12-16 hours (adjusted for distributed state complexity)
**Complexity**: High
**Risk**: High (distributed execution state management)

**Why**: Core distributed execution capability. This enables workload distribution across workers.

**Acceptance Criteria**:
- [ ] API submits Ray tasks via `execute_script.remote(exec_id)`
- [ ] Ray schedules task on available worker
- [ ] Execution status updates in database: queued → running → completed
- [ ] Handle edge cases: job claiming races across workers
- [ ] Handle edge cases: network partitions during execution
- [ ] Handle edge cases: state reconciliation after worker death
- [ ] Multi-worker job distribution verified (jobs spread evenly)
- [ ] Atomic job claiming prevents double-execution

**Success Metric**: 10 jobs distributed across 3 workers with even load, no double-execution

**Story File**: `docs/sprint-artifacts/stories/3-3-ray-task-submission.md`

---

#### Story 3-4: Implement Worker Health Monitoring
**Epic**: Epic 3 - Distributed Orchestration
**Priority**: Critical
**Estimate**: 8-12 hours
**Complexity**: High
**Risk**: High (distributed systems failure scenarios)

**Why**: Detect dead workers to prevent jobs from being stuck forever.

**Acceptance Criteria**:
- [ ] Workers send heartbeats every 30 seconds to worker_heartbeats table
- [ ] Orchestrator checks heartbeats periodically
- [ ] Orchestrator marks worker as dead if no heartbeat for 2 minutes
- [ ] Orphaned tasks (running on dead worker) are rescheduled to other workers
- [ ] Heartbeat table: worker_id, last_heartbeat_at

**Success Metric**: Kill worker mid-job, job rescheduled to another worker within 3 minutes

**Story File**: `docs/sprint-artifacts/stories/3-4-worker-health-monitoring.md`

---

### Phase 4: Hetzner Provisioning

#### Story 4-1: Implement Hetzner Worker Provisioning via API
**Epic**: Epic 4 - Cloud Infrastructure
**Priority**: Critical
**Estimate**: 10-14 hours
**Complexity**: High
**Risk**: High (cloud API, networking, timing)

**Why**: Auto-scale capacity based on workload. Makes infrastructure invisible.

**Acceptance Criteria**:
- [ ] Orchestrator calls Hetzner API to create CX22 server
- [ ] Server type: cx22 (2 vCPU, 4GB RAM, €5.83/month prorated)
- [ ] Cloud-init script installs Docker, Ray, runner
- [ ] Worker joins Ray cluster within 60 seconds
- [ ] Worker record created in workers table (worker_id, created_at, region)
- [ ] Use Hetzner Python SDK (hcloud)
- [ ] Cloud-init template in infra/cloud-init/worker.yaml

**Success Metric**: Provision worker via API, worker joins cluster and accepts jobs within 90 seconds

**Story File**: `docs/sprint-artifacts/stories/4-1-hetzner-provisioning.md`

---

#### Story 4-2: Implement Queue-Based Smart Provisioning Algorithm
**Epic**: Epic 4 - Cloud Infrastructure
**Priority**: Critical
**Estimate**: 8-12 hours
**Complexity**: High
**Risk**: Medium (algorithm correctness)

**Why**: Minimize costs while maintaining responsiveness. Prevent over-provisioning.

**Acceptance Criteria**:
- [ ] Orchestrator runs provisioning check every 10 seconds
- [ ] Calculate: `queued_jobs = count(status='queued')`
- [ ] Calculate: `available_slots = sum(worker.max_concurrent for idle workers)`
- [ ] Calculate: `est_completion_time` based on running jobs
- [ ] If `available_slots >= queued_jobs`, provision = 0
- [ ] If `est_completion_time < 5 minutes`, provision = 0 (jobs completing soon)
- [ ] Else: provision = `ceil((queued_jobs - available_slots) / 2)` workers
- [ ] Each CX22 has 2 slots (1 job per vCPU)

**Success Metric**: Various queue depths trigger correct provisioning decisions (no over-provisioning)

**Story File**: `docs/sprint-artifacts/stories/4-2-smart-provisioning-algorithm.md`

---

#### Story NEW-4: Implement Provisioning User Feedback
**Epic**: New (UX improvement)
**Priority**: High
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (UI/messaging)

**Why**: Users need visibility into provisioning process. 60-second wait feels long without feedback.

**Acceptance Criteria**:
- [ ] Display provisioning status: "Provisioning worker... (30s elapsed)"
- [ ] CLI spinner/progress during 60-second worker startup
- [ ] Error for Hetzner quota exceeded: "Worker limit reached. Upgrade account or wait for workers to free up."
- [ ] Error for API failures: "Cloud provider error. Retrying... (attempt 2/3)"
- [ ] Error for network issues: "Cannot reach cloud provider. Check network connection."
- [ ] Simulate various failure modes in tests

**Success Metric**: User sees clear feedback for provisioning success and all failure modes

**Story File**: `docs/sprint-artifacts/stories/NEW-4-provisioning-user-feedback.md`

---

### Phase 5: Worker Lifecycle Management

#### Story NEW-7: Implement Dead Worker Detection with Heartbeats
**Epic**: Deferred from Tier 3
**Priority**: Critical
**Estimate**: 10-14 hours (adjusted for failure scenario complexity)
**Complexity**: High
**Risk**: High (distributed failure detection)

**Why**: Enhanced worker health monitoring with database-driven detection and auto-replacement integration.

**Acceptance Criteria**:
- [ ] Enhanced heartbeat monitoring (builds on Story 3-4)
- [ ] Database-driven dead worker detection
- [ ] Integration with provisioning for auto-replacement
- [ ] Orchestrator periodic cleanup job
- [ ] Comprehensive failure injection testing

**Success Metric**: Simulate worker failures, verify detection and replacement within 3 minutes

**Story File**: `docs/sprint-artifacts/stories/NEW-7-dead-worker-detection.md`

---

#### Story 4-5: Implement Worker Auto-Replacement on Failure
**Epic**: Epic 4 - Cloud Infrastructure
**Priority**: Critical
**Estimate**: 8-12 hours
**Complexity**: High
**Risk**: High (coordination of detection, provisioning, rescheduling)

**Why**: Self-healing system. Workers fail in production - system must recover automatically.

**Acceptance Criteria**:
- [ ] Detect dead workers (no heartbeat for 2 minutes)
- [ ] Provision replacement worker via Hetzner API
- [ ] Reschedule orphaned jobs to new worker
- [ ] Terminate dead worker via Hetzner API
- [ ] Worker record marked as terminated in database
- [ ] Chaos testing: kill workers, verify replacement and job completion

**Success Metric**: Kill 2 workers during batch job, both replaced, all jobs complete successfully

**Story File**: `docs/sprint-artifacts/stories/4-5-worker-auto-replacement.md`

---

#### Story 4-3: Implement Billing Hour Aware Worker Termination
**Epic**: Epic 4 - Cloud Infrastructure
**Priority**: High
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (time-based logic)

**Why**: Maximize value from hourly billing. Hetzner bills hourly - keep workers alive until billing hour ends.

**Acceptance Criteria**:
- [ ] Track worker provisioned time T
- [ ] When worker completes all jobs, check: `current_time < T + 1 hour`?
- [ ] If yes, keep worker alive (idle)
- [ ] If no, terminate worker via Hetzner API
- [ ] Worker record marked as terminated in database
- [ ] Cost amortization across jobs in billing hour (Epic 9 dependency)

**Success Metric**: Workers stay alive until billing hour ends, terminate after

**Story File**: `docs/sprint-artifacts/stories/4-3-billing-hour-termination.md`

---

### Phase 6: Worker Optimization

#### Story 4-4: Pre-Pull Common Docker Images on Worker Init
**Epic**: Epic 4 - Cloud Infrastructure
**Priority**: High
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (straightforward Docker commands)

**Why**: Minimize cold-start latency. First job on new worker shouldn't wait for image pull.

**Acceptance Criteria**:
- [ ] Cloud-init pre-pulls python:3.11-slim
- [ ] Cloud-init pre-pulls python:3.10-slim
- [ ] Cloud-init pre-pulls custom datascience image
- [ ] Cloud-init pre-pulls custom ffmpeg image
- [ ] Cloud-init pre-pulls node:20
- [ ] Images cached locally on worker
- [ ] First execution using these runtimes starts immediately (no pull delay)
- [ ] Pre-pull takes ~2-3 minutes during worker boot (acceptable)

**Success Metric**: Measure cold-start time with and without pre-pull - verify no pull delay

**Story File**: `docs/sprint-artifacts/stories/4-4-pre-pull-docker-images.md`

---

## Test Plan (REQUIRED)

### Test Strategy

**Testing Approach**: TDD (Test-Driven Development) for critical stories, test-after for low-complexity stories

**Coverage Goals**:
- Unit tests: 80% of new code (provisioning logic, scheduling algorithms)
- Integration tests: All distributed execution workflows
- Chaos engineering: 2-3 days dedicated testing
- Manual tests: Actual Hetzner provisioning in staging

### Baseline Metrics (BEFORE Tier 4)

Collect these metrics BEFORE starting Tier 4 for comparison:

- [ ] Single-node max throughput (jobs/minute)
- [ ] Database query performance under load (50+ concurrent queries)
- [ ] Docker container startup time at scale (10+ concurrent containers)

### Test Cases by Phase

#### Phase 1: File Handling (Story 2-5)

**Unit Tests** (`tests/unit/test_file_handling.py`):
1. `test_detect_file_arguments()` - CLI detects file vs string args
2. `test_generate_presigned_put_url()` - MinIO presigned URL generation
3. `test_file_upload_to_minio()` - Upload files to MinIO
4. `test_runner_downloads_files()` - Runner downloads from MinIO to container

**Integration Tests** (`tests/integration/test_file_handling_e2e.py`):
1. `test_end_to_end_file_upload_and_execution()` - Full workflow with 10MB file
2. `test_multiple_input_files()` - Script with 3 input files

**Expected Test Count**: 4 unit tests, 2 integration tests

---

#### Phase 2: Ray Cluster (Stories 3-1, 3-2)

**Unit Tests** (`tests/unit/test_ray_cluster.py`):
1. `test_ray_head_initialization()` - Ray head node starts correctly
2. `test_ray_worker_connection()` - Worker connects to head node

**Integration Tests** (`tests/integration/test_ray_cluster.py`):
1. `test_ray_dashboard_accessible()` - Dashboard at localhost:8265
2. `test_worker_registration()` - Worker appears in Ray cluster
3. `test_worker_advertises_resources()` - Worker shows 2 CPU, 4GB RAM

**Expected Test Count**: 2 unit tests, 3 integration tests

---

#### Phase 3: Ray Task Distribution (Stories 3-3, 3-4)

**Unit Tests** (`tests/unit/test_ray_tasks.py`):
1. `test_submit_ray_task()` - Task submission via execute_script.remote()
2. `test_atomic_job_claiming()` - Prevent double-execution
3. `test_heartbeat_recording()` - Heartbeats stored in database
4. `test_dead_worker_detection()` - Worker marked dead after 2min timeout

**Integration Tests** (`tests/integration/test_distributed_execution.py`):
1. `test_multi_worker_distribution()` - 10 jobs across 3 workers, even load
2. `test_job_rescheduling_on_worker_death()` - Kill worker mid-job, verify reschedule
3. `test_network_partition_recovery()` - Simulate network partition

**Chaos Engineering** (`tests/integration/test_chaos.py`):
1. `test_kill_worker_mid_execution()` - Forcefully kill worker process
2. `test_network_partition_during_task()` - Disconnect worker network
3. `test_database_connection_loss()` - Simulate DB connection failure

**Expected Test Count**: 4 unit tests, 3 integration tests, 3 chaos tests

---

#### Phase 4: Hetzner Provisioning (Stories 4-1, 4-2, NEW-4)

**Unit Tests** (`tests/unit/test_hetzner_provisioning.py`):
1. `test_calculate_provisioning_need()` - Smart provisioning algorithm
2. `test_create_cloud_init_config()` - Cloud-init YAML generation
3. `test_hetzner_api_call()` - Mock Hetzner API call

**Integration Tests** (`tests/integration/test_hetzner_provisioning.py`):
1. `test_provision_worker_e2e()` - Provision actual Hetzner worker (staging)
2. `test_worker_joins_cluster()` - Provisioned worker joins Ray cluster within 90s
3. `test_queue_depth_triggers_provisioning()` - Various queue depths

**Manual Tests**:
- [ ] Provision worker in Hetzner console, verify in dashboard
- [ ] Test Hetzner quota exceeded scenario
- [ ] Test Hetzner API failure scenarios
- [ ] Verify user-friendly error messages

**Expected Test Count**: 3 unit tests, 3 integration tests, 4 manual tests

---

#### Phase 5: Worker Lifecycle (Stories NEW-7, 4-5, 4-3)

**Unit Tests** (`tests/unit/test_worker_lifecycle.py`):
1. `test_billing_hour_calculation()` - Billing hour logic
2. `test_worker_termination_decision()` - Terminate or keep alive?

**Integration Tests** (`tests/integration/test_worker_lifecycle.py`):
1. `test_worker_kept_alive_until_billing_hour()` - Worker stays alive <1hr
2. `test_worker_terminated_after_billing_hour()` - Worker terminates >1hr
3. `test_auto_replacement_on_failure()` - Dead worker replaced, jobs rescheduled

**Chaos Engineering**:
1. `test_kill_multiple_workers_simultaneously()` - Kill 2 workers at once
2. `test_worker_failure_during_batch()` - Kill worker during 100-job batch

**Expected Test Count**: 2 unit tests, 3 integration tests, 2 chaos tests

---

#### Phase 6: Optimization (Story 4-4)

**Unit Tests**: None (cloud-init configuration)

**Integration Tests** (`tests/integration/test_worker_optimization.py`):
1. `test_images_present_on_boot()` - Verify pre-pulled images
2. `test_cold_start_performance()` - Measure first execution time

**Expected Test Count**: 0 unit tests, 2 integration tests

---

### Manual Testing Checklist

For features requiring manual validation:

- [ ] Provision Hetzner worker via dashboard, verify joins cluster
- [ ] Test Hetzner quota exceeded scenario (hit account limits)
- [ ] Test Hetzner API downtime (use mock or staging)
- [ ] Verify CLI provisioning feedback messages
- [ ] Load test with 100+ concurrent jobs across distributed workers
- [ ] Verify Ray dashboard shows all workers and tasks
- [ ] Test network partition scenarios (disconnect worker network)
- [ ] Verify billing hour termination logic with real timestamps

### Test Execution Timeline

- [ ] **Before implementation**: Collect baseline metrics (single-node throughput, DB performance, Docker startup)
- [ ] **Before Tier 4**: Write failing tests for Story 2-5 (TDD)
- [ ] **During implementation**: Tests turn green incrementally for each story
- [ ] **After each story**: Run story-specific tests, verify passing
- [ ] **Mid-tier (after Phase 3)**: Run chaos engineering tests (2-3 days dedicated)
- [ ] **After Tier 4 complete**: Full test suite passes (unit + integration + chaos)
- [ ] **Before commit**: Run full test suite locally, all passing
- [ ] **After tier completion**: Create TIER4_TEST_REPORT.md

---

## Estimates

| Story | Priority | Estimate | Type |
|-------|----------|----------|------|
| 2-5 | Critical | 4-6h | File I/O |
| 3-1 | Critical | 6-8h | Infrastructure |
| 3-2 | Critical | 6-8h | Infrastructure |
| 3-3 | Critical | 12-16h | Distributed Systems |
| 3-4 | Critical | 8-12h | Distributed Systems |
| 4-1 | Critical | 10-14h | Cloud API |
| 4-2 | Critical | 8-12h | Algorithm |
| NEW-4 | High | 4-6h | UX |
| NEW-7 | Critical | 10-14h | Distributed Systems |
| 4-5 | Critical | 8-12h | Cloud Lifecycle |
| 4-3 | High | 6-8h | Cost Optimization |
| 4-4 | High | 4-6h | Performance |

**Total (Critical)**: ~96-136 hours
**Total (Critical + High)**: ~110-154 hours
**Total (All Stories)**: ~110-154 hours (4-5 weeks)

**Note**: Estimates include 20-30% complexity buffer based on developer review

---

## Implementation Strategy

### Phase 1: File Handling Foundation (Week 1)
1. Story 2-5 (MinIO file upload/download)

**Goal**: Files work across distributed execution

### Phase 2-3: Ray Cluster & Distribution (Week 1-2)
2. Story 3-1 (Ray head node)
3. Story 3-2 (Ray worker init)
4. Story 3-3 (Ray task submission)
5. Story 3-4 (Worker health monitoring)

**Goal**: Distributed execution functional

### Chaos Engineering (Mid-Tier, 2-3 days)
- Dedicated testing period after Phase 3
- Kill workers, network partitions, DB failures
- Verify recovery mechanisms

### Phase 4: Hetzner Provisioning (Week 3)
6. Story 4-1 (Hetzner API provisioning)
7. Story 4-2 (Smart provisioning algorithm)
8. Story NEW-4 (Provisioning user feedback)

**Goal**: Auto-scaling infrastructure works

### Phase 5: Worker Lifecycle (Week 4)
9. Story NEW-7 (Dead worker detection)
10. Story 4-5 (Auto-replacement)
11. Story 4-3 (Billing hour termination)

**Goal**: Self-healing, cost-optimized infrastructure

### Phase 6: Optimization (Week 5)
12. Story 4-4 (Pre-pull images)

**Goal**: Performance optimization complete

---

## Dependencies

**Prerequisites**:
- [x] Tier 3 completed (production-ready single-node)
- [x] Alembic database migrations in place
- [x] Container resource limits working
- [x] Job timeout mechanism working
- [ ] Hetzner account created with API credentials
- [ ] Hetzner account limits increased (request before starting)
- [ ] MinIO cluster deployed and accessible

**Blocks**:
- This tier blocks Security Review milestone
- This tier blocks Tier 4.5 (Batch Quick Win)
- Specifically blocks all batch execution features

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ray cluster networking issues | Medium | High | Test locally with Docker Compose Ray cluster first; Fallback: Direct API polling |
| Hetzner API reliability (failures, rate limits) | Medium | High | Add retry logic, handle rate limits, monitor API status |
| Hetzner account limits exceeded | Medium | High | Request limit increase before starting; Fallback: DigitalOcean as backup provider |
| Worker failure scenarios not handled | High | High | Comprehensive chaos engineering (2-3 days dedicated), test all failure modes |
| Distributed state consistency issues | Medium | High | Use database as source of truth, implement idempotent operations |
| Cloud-init timing issues (worker doesn't join cluster) | Medium | Medium | Extensive testing with actual Hetzner provisioning, add retry logic |
| MinIO network issues across workers | Low | Medium | Test MinIO access from provisioned workers, verify presigned URLs work |

---

## Definition of Done

**Story-level**:
- [ ] Story file created in `docs/sprint-artifacts/stories/`
- [ ] All acceptance criteria met (verified by tests)
- [ ] Unit tests written and passing (80%+ coverage for story code)
- [ ] Integration tests written and passing (critical workflows)
- [ ] Manual testing performed (if applicable)
- [ ] Code reviewed (self-review minimum)
- [ ] No regressions (existing 83 tests still pass)
- [ ] Committed and pushed to main
- [ ] Pre-commit hook passed (tests run automatically)

**Tier-level**:
- [ ] All critical stories completed and tested (Stories 2-5, 3-1 through 3-4, 4-1, 4-2, NEW-7, 4-5)
- [ ] All high-priority stories completed and tested (NEW-4, 4-3, 4-4)
- [ ] Chaos engineering tests completed (2-3 days, all scenarios tested)
- [ ] Baseline metrics collected (before Tier 4)
- [ ] Load testing with 100+ concurrent jobs across distributed workers
- [ ] Manual Hetzner provisioning tested in staging environment
- [ ] TIER4_SUMMARY.md created documenting what was done
- [ ] TIER4_TEST_REPORT.md created with test results and coverage metrics
- [ ] Sprint status updated (docs/sprint-artifacts/sprint-status.yaml if exists)
- [ ] TIER4_RETROSPECTIVE.md completed (lessons learned, what worked, what didn't)
- [ ] System meets tier objectives (distributed execution, auto-scaling)
- [ ] CLI help text updated with cloud execution guidance
- [ ] Documentation: "Cloud Execution" guide added to docs/
- [ ] Ready for Security Review milestone

---

## Success Criteria

**This tier is successful when**:
1. Jobs distributed across 3+ workers automatically (measured: 10 jobs → 3 workers, even load)
2. Workers auto-provision when queue depth increases (measured: 20 queued jobs → 10 workers provisioned)
3. Workers auto-terminate after billing hour ends (measured: idle worker terminated after 60min)
4. Dead workers detected and replaced within 3 minutes (measured: kill worker, verify replacement)
5. Files upload/download correctly across distributed execution (measured: 10MB file processed)
6. No manual infrastructure management required (measured: zero manual intervention in 100-job test)

**Production Readiness**: 60% ready for production after this tier
- Distributed execution works
- Auto-scaling works
- Still needs: Security Review, batch execution, caching, observability

---

## Notes

**Security Considerations**:
- After Tier 4, MANDATORY Security Review milestone before proceeding
- Multi-tenant code execution requires rigorous security audit
- See Security Review section in TIER_ROADMAP.md

**Cost Considerations**:
- Hetzner CX22: €5.83/month prorated (€0.009/hour)
- Smart provisioning algorithm minimizes over-provisioning
- Billing hour termination maximizes value from hourly billing
- Full cost tracking in Tier 6 (Epic 9)

**Architectural Decisions**:
- Ray chosen for distributed task scheduling (proven, mature)
- Hetzner chosen for cost efficiency (vs AWS/GCP)
- MinIO for S3-compatible storage (self-hosted, no vendor lock-in)
- Database as source of truth for distributed state

**Related Documents**:
- docs/PRD.md - Product requirements
- docs/ARCHITECTURE.md - Technical architecture decisions
- docs/epics.md - Full story details with acceptance criteria
- docs/TIER_ROADMAP.md - Complete roadmap for Tiers 4-6
- docs/TIER3_RETROSPECTIVE.md - Learnings from Tier 3

**Party Mode Review**:
This plan incorporates recommendations from 10-agent party mode review:
- Effort estimates adjusted +20-30% for high complexity (Amelia/Developer)
- NEW-4 story added for provisioning user feedback (Sally/UX Designer)
- Chaos engineering testing added (Murat/TEA)
- Missing risks documented (Mary/Analyst)
- Documentation deliverables added (Paige/Tech Writer)

---

## Checklist Before Starting

- [ ] This plan reviewed and approved
- [ ] Hetzner account created with API credentials stored securely
- [ ] Hetzner account limits verified/increased
- [ ] MinIO cluster deployed and accessible from control plane
- [ ] All story files created in sprint-artifacts/stories/ (14 files)
- [ ] Test plan clearly understood (unit + integration + chaos)
- [ ] Dependencies verified (Tier 3 complete, migrations working)
- [ ] Risks identified and mitigation strategies clear
- [ ] Definition of done understood by dev team
- [ ] Estimated time is realistic (4-5 weeks for 14 stories)
- [ ] Baseline metrics collection plan ready
- [ ] Docker Compose Ray cluster setup for local testing
- [ ] Staging environment ready for Hetzner testing

---

**Plan Status**: Ready for Dev
**Next Step**: Activate DEV (Amelia) to execute stories
**Expected Duration**: 4-5 weeks (110-154 hours)
**Target Completion**: [Date TBD based on start date]

---

**Created by**: Bob (Scrum Master)
**Date**: 2025-11-15
**Template Version**: 1.0
**Review Status**: Ready for team review and approval
