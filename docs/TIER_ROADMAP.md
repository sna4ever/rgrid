# RGrid Implementation Roadmap: Tiers 4-6

**Author:** Winston (Architect Agent)
**Date:** 2025-11-15
**Status:** Active Planning Document
**Scope:** Post-MVP implementation roadmap

---

## Executive Summary

This document provides the strategic implementation roadmap for RGrid Tiers 4-6, building upon the foundation established in Tiers 1-3. Each tier delivers incremental, production-ready value while maintaining technical coherence and managing implementation risk.

### Completed Foundation (Tiers 1-3)

**Tier 1: Walking Skeleton** ✅
- Monorepo structure, FastAPI backend, CLI framework
- Basic Docker execution, simplified auth
- Database schema, basic file detection
- **Value:** Core data flow proven on localhost

**Tier 2: Demo-Ready** ✅
- Worker daemon with atomic job claiming
- Output capture to database
- `rgrid status` and `rgrid logs` commands
- Environment variables, arguments support
- **Value:** End-to-end execution without manual intervention

**Tier 3: Production-Ready Core** ✅
- Alembic database migrations
- Container resource limits (512MB, 1 CPU)
- Job timeout mechanism (5 minutes)
- Pre-configured runtimes (python, node, etc.)
- **Value:** Production reliability for single-node execution

### Current System Capabilities

After Tier 3, RGrid can:
- ✅ Submit jobs via CLI
- ✅ Execute scripts in isolated containers
- ✅ Enforce resource limits and timeouts
- ✅ Capture and display logs
- ✅ Use friendly runtime names
- ✅ Safely evolve database schema

### What's Missing (Tiers 4-6)

The remaining 46 stories fall into four strategic milestones:

| Tier | Theme | Stories | Estimated Effort |
|------|-------|---------|------------------|
| **Tier 4** | Distributed Execution & Cloud | 14 stories | 4-5 weeks |
| **Security Review** | Multi-tenant security audit | Milestone | 1 week |
| **Tier 4.5** | Batch Quick Win | 2 stories | 1 week |
| **Tier 5** | Advanced Features & Optimization | 15 stories | 4-5 weeks |
| **Tier 6** | Production Polish & Interfaces | 14 stories | 4-5 weeks |

**Total:** 46 stories + 1 security milestone, 14-17 weeks estimated

**Party Mode Review Applied:** Incorporated recommendations from multi-agent review (2025-11-15)

---

## Tier 4: Distributed Execution & Cloud Infrastructure

**Theme:** Enable horizontal scaling and elastic compute

**Goal:** Transform RGrid from single-node to distributed execution with auto-scaling Hetzner workers

**Value Delivered:**
- Horizontal scaling across multiple workers
- Automatic cloud provisioning and termination
- Cost-efficient billing hour optimization
- Reliable worker health monitoring
- Complete file upload/download workflow

### Prerequisites

- ✅ Tier 3 complete (single-node execution reliable)
- ✅ Database migrations in place
- ✅ Resource limits and timeouts working

### Stories (14 total)

**Note:** Effort estimates adjusted +20-30% based on developer review of complexity

#### Phase 1: File Handling Foundation (1 story)
**Why first:** File handling must work before distributing jobs across nodes

**2-5: Handle Script Input Files as Arguments** (Epic 2)
- Full MinIO integration for file uploads
- Presigned PUT URLs for CLI uploads
- Runner downloads files into container
- **Complexity:** Medium
- **Risk:** Low (MinIO SDK well-documented)
- **Estimated effort:** 4-6 hours
- **Dependencies:** None
- **Tests:** Upload files >10MB, verify downloads in container

---

#### Phase 2: Ray Cluster Setup (2 stories)
**Why second:** Foundation for distributed task scheduling

**3-1: Set Up Ray Head Node on Control Plane** (Epic 3)
- Ray head node as separate container
- Serves on port 6379 (Redis protocol)
- Dashboard on port 8265
- Workers connect via private IP (10.0.0.1:6379)
- **Complexity:** Medium
- **Risk:** Medium (Ray cluster networking)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None
- **Tests:** Ray dashboard accessible, workers can connect

**3-2: Initialize Ray Worker on Each Hetzner Node** (Epic 3)
- Cloud-init script starts Ray worker on boot
- Worker connects to head node
- Advertises max_concurrent = 2 (1 job per vCPU)
- **Complexity:** Medium
- **Risk:** Medium (cloud-init timing issues)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 3-1
- **Tests:** Worker appears in Ray dashboard, accepts tasks

---

#### Phase 3: Ray Task Distribution (2 stories)
**Why third:** Enable distributed job execution

**3-3: Submit Executions as Ray Tasks** (Epic 3)
- API submits Ray tasks via `execute_script.remote(exec_id)`
- Ray schedules tasks on available workers
- Status updates: queued → running → completed
- Handle edge cases: job claiming races, network partitions, state reconciliation
- **Complexity:** High
- **Risk:** High (distributed execution state management)
- **Estimated effort:** 12-16 hours (adjusted for distributed state complexity)
- **Dependencies:** 3-2
- **Tests:** Multi-worker job distribution, verify atomic claiming, chaos testing

**3-4: Implement Worker Health Monitoring** (Epic 3)
- Workers send heartbeats every 30 seconds
- Orchestrator detects dead workers (2-minute timeout)
- Orphaned tasks rescheduled to other workers
- **Complexity:** High
- **Risk:** High (distributed systems failure scenarios)
- **Estimated effort:** 8-12 hours
- **Dependencies:** 3-3
- **Tests:** Kill worker mid-job, verify rescheduling

---

#### Phase 4: Hetzner Provisioning (2 stories)
**Why fourth:** Auto-scale infrastructure based on workload

**4-1: Implement Hetzner Worker Provisioning via API** (Epic 4)
- Orchestrator provisions CX22 servers via Hetzner API
- Cloud-init installs Docker, Ray, runner
- Worker joins Ray cluster within 60 seconds
- **Complexity:** High
- **Risk:** High (cloud API, networking, timing)
- **Estimated effort:** 10-14 hours
- **Dependencies:** 3-2
- **Tests:** Provision worker, verify it joins cluster and accepts jobs

**4-2: Implement Queue-Based Smart Provisioning Algorithm** (Epic 4)
- Check queue depth every 10 seconds
- Calculate: `available_slots`, `queued_jobs`, `est_completion_time`
- Smart provisioning: avoid over-provisioning
- **Complexity:** High
- **Risk:** Medium (algorithm correctness)
- **Estimated effort:** 8-12 hours
- **Dependencies:** 4-1
- **Tests:** Various queue depths, verify provisioning decisions

**NEW-4: Implement Provisioning User Feedback** (New story from UX review)
- Display provisioning status to user: "Provisioning worker... (30s elapsed)"
- Error messages for provisioning failures:
  - Hetzner quota exceeded: "Worker limit reached. Upgrade account or wait for workers to free up."
  - API failures: "Cloud provider error. Retrying... (attempt 2/3)"
  - Network issues: "Cannot reach cloud provider. Check network connection."
- CLI spinner/progress during 60-second worker startup
- **Complexity:** Low
- **Risk:** Low (UI/messaging)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 4-1, 4-2
- **Tests:** Simulate various failure modes, verify user-friendly messages

---

#### Phase 5: Worker Lifecycle Management (3 stories)
**Why fifth:** Optimize costs and reliability

**NEW-7: Implement Dead Worker Detection with Heartbeats** (Deferred from Tier 3)
- Enhanced heartbeat monitoring (builds on 3-4)
- Database-driven dead worker detection
- Integration with provisioning for auto-replacement
- **Complexity:** High
- **Risk:** High (distributed failure detection)
- **Estimated effort:** 10-14 hours (adjusted for failure scenario complexity)
- **Dependencies:** 3-4, 4-1
- **Tests:** Simulate worker failures, verify detection and replacement, chaos engineering

**4-5: Implement Worker Auto-Replacement on Failure** (Epic 4)
- Detect dead workers (no heartbeat for 2 minutes)
- Provision replacement worker
- Reschedule orphaned jobs
- Terminate dead worker via Hetzner API
- **Complexity:** High
- **Risk:** High (coordination of detection, provisioning, rescheduling)
- **Estimated effort:** 8-12 hours
- **Dependencies:** NEW-7, 4-2
- **Tests:** Kill workers, verify replacement and job completion

**4-3: Implement Billing Hour Aware Worker Termination** (Epic 4)
- Keep workers alive until billing hour ends
- Terminate idle workers after billing hour
- Maximize cost amortization
- **Complexity:** Medium
- **Risk:** Low (time-based logic)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 4-2
- **Tests:** Verify workers stay alive until hour ends, terminate after

---

#### Phase 6: Worker Optimization (1 story)
**Why last:** Performance optimization after core functionality works

**4-4: Pre-Pull Common Docker Images on Worker Init** (Epic 4)
- Cloud-init pre-pulls python:3.11, python:3.10, datascience, ffmpeg, node
- Images cached locally on worker
- First execution starts immediately (no pull delay)
- **Complexity:** Low
- **Risk:** Low (straightforward Docker commands)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 4-1
- **Tests:** Verify images present on worker boot, measure cold-start time

---

### Tier 4 Summary

**Total Stories:** 14
**Estimated Effort:** 110-154 hours (4-5 weeks, includes 20% complexity buffer)
**Critical Path:** 3-1 → 3-2 → 3-3 → 3-4 → 4-1 → 4-2 → NEW-4 → 4-5

**Key Risks:**
1. **Ray cluster networking** - Mitigation: Test locally with Docker Compose Ray cluster first; Fallback: Direct API polling
2. **Hetzner API reliability** - Mitigation: Add retry logic, handle rate limits, monitor API status
3. **Hetzner account limits** (NEW from analyst review) - Mitigation: Request limit increase before starting; Fallback: DigitalOcean as backup provider
4. **Worker failure scenarios** - Mitigation: Comprehensive chaos engineering testing (2-3 days dedicated)
5. **Distributed state consistency** - Mitigation: Use database as source of truth, implement idempotent operations

**Success Criteria:**
- ✅ Jobs distributed across 3+ workers automatically
- ✅ Workers auto-provision when queue depth increases
- ✅ Workers auto-terminate after billing hour ends
- ✅ Dead workers detected and replaced within 3 minutes
- ✅ Files upload/download correctly across distributed execution
- ✅ No manual infrastructure management required

**Testing Requirements:**
- **Unit tests:** All provisioning and scheduling logic (80%+ coverage)
- **Integration tests:** Local Ray cluster with 3+ workers
- **Baseline metrics** (BEFORE Tier 4):
  - Single-node max throughput
  - Database query performance under load
  - Docker container startup times at scale
- **Chaos engineering** (2-3 days dedicated):
  - Kill workers mid-execution
  - Simulate network partitions
  - Force Hetzner API failures
  - Corrupt database state and verify recovery
- **Manual testing:** Actual Hetzner provisioning in staging environment
- **Load testing:** 100+ concurrent jobs across distributed workers
- **Documentation:** CLI help text updates, "Cloud Execution" guide added to docs

---

## Security Review Milestone

**When:** After Tier 4 complete, before Tier 4.5

**Duration:** 1 week

**Goal:** Comprehensive security audit of multi-tenant cloud infrastructure before adding batch capabilities

### Scope

RGrid executes untrusted user code in a multi-tenant environment with cloud infrastructure. This requires rigorous security review before public release.

**Critical Areas to Audit:**

1. **Container Isolation**
   - Verify Docker container sandboxing (network=none, read-only root)
   - Test resource limits enforcement (CPU, memory)
   - Verify no container escape vectors
   - Test process isolation between concurrent jobs

2. **Multi-Tenancy**
   - Verify complete isolation between accounts
   - Test API key authentication and authorization
   - Verify database row-level security (account_id filtering)
   - Test artifact access controls (presigned URLs scoped to account)

3. **Cloud Infrastructure**
   - Hetzner API key storage and rotation
   - Worker node security hardening
   - Network security groups and firewall rules
   - MinIO access policies and bucket isolation

4. **Input Validation**
   - Script content sanitization
   - File upload validation (size limits, type checking)
   - Environment variable injection prevention
   - SQL injection prevention (parameterized queries)

5. **Secrets Management**
   - API keys never logged or exposed in errors
   - MinIO credentials rotation
   - Database connection strings secured
   - Worker-to-control-plane authentication

### Deliverables

- **Security Audit Report** (docs/SECURITY_AUDIT.md)
  - Findings categorized by severity (Critical, High, Medium, Low)
  - Remediation recommendations
  - Attack surface analysis

- **Penetration Testing Results**
  - Attempt container escape
  - Attempt cross-account access
  - Attempt resource exhaustion attacks
  - Attempt data exfiltration

- **Security Hardening Checklist**
  - All critical and high findings resolved
  - Medium findings documented with acceptance or plan
  - Security best practices documented for future development

### Success Criteria

- ✅ Zero critical security findings unresolved
- ✅ All high-severity findings resolved or mitigated
- ✅ Penetration testing shows no exploitable vulnerabilities
- ✅ Security hardening guide created for operations team
- ✅ Incident response plan documented

**Note:** This milestone is MANDATORY before public MVP release. Do not skip.

---

## Tier 4.5: Batch Quick Win

**Theme:** Deliver immediate user-facing value with basic batch execution

**Goal:** Give users the `--batch` flag immediately after distributed execution works

**Value Delivered:**
- Users can process multiple files in parallel
- Clear demonstration of distributed execution benefits
- Natural demo point after infrastructure work

**Why This Tier?** Product management feedback: Tier 4 enables infrastructure but users don't see value. Tier 4.5 delivers the killer feature (batch execution) as soon as distribution works, creating a natural demo milestone.

### Prerequisites

- ✅ Tier 4 complete (distributed execution working)
- ✅ Security Review complete
- ✅ File upload/download working (Story 2-5 from Tier 4)

### Stories (2 total)

**5-1: Implement --batch Flag with Glob Pattern Expansion** (Epic 5)
- Expand glob patterns (*.csv, data/**, etc.)
- Create N execution requests (one per file)
- Display: "Starting batch: 100 files, 10 parallel"
- **Complexity:** Medium
- **Risk:** Low (Python glob library)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 2-5 (file handling from Tier 4)
- **Tests:** Various glob patterns, verify execution count

**5-2: Implement --parallel Flag for Concurrency Control** (Epic 5)
- Control max parallel executions
- Use asyncio.Semaphore for concurrency
- Default parallelism = 10
- **Complexity:** Medium
- **Risk:** Medium (async coordination)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 5-1
- **Tests:** Verify max parallelism enforced, measure throughput

### Tier 4.5 Summary

**Total Stories:** 2
**Estimated Effort:** 12-16 hours (1 week with testing and docs)
**Critical Path:** 5-1 → 5-2

**Value Delivered:** Users can now run `rgrid run script.py --batch data/*.csv --parallel 20` and see jobs distributed across cloud workers automatically.

**Success Criteria:**
- ✅ Users can batch-process 100+ files with single command
- ✅ Parallelism controls work correctly
- ✅ Jobs distributed across multiple cloud workers
- ✅ Demo-ready for showcasing distributed batch execution

**Testing Requirements:**
- Various glob patterns (*.csv, data/**, file_{1..100}.json)
- Parallelism limits enforced correctly
- Load testing with 100+ file batch
- **Documentation:** Batch execution tutorial with examples added to docs

**Demo Milestone:** After Tier 4.5, RGrid can be demoed as "process 1000 CSV files in parallel across auto-scaling cloud workers with one command."

---

## Tier 5: Advanced Features & Optimization

**Theme:** Batch management, caching, and complete file management

**Goal:** Complete batch execution features and add content-hash caching for instant re-runs

**Value Delivered:**
- Advanced batch management (progress tracking, failure handling, retry)
- Content-hash caching for instant re-runs
- Complete artifact management with MinIO
- Auto-detect Python dependencies
- Large file streaming and compression

### Prerequisites

- ✅ Tier 4.5 complete (basic batch execution working)
- ✅ Ray cluster operational
- ✅ Hetzner auto-scaling functional
- ✅ File upload/download working

### Stories (15 total)

**Note:** Stories 5-1 and 5-2 moved to Tier 4.5 for immediate user value

#### Phase 1: MinIO Storage Foundation (2 stories)
**Why first:** Storage infrastructure needed for all artifact management

**7-2: Auto-Collect Output Files from Container** (Epic 7)
- Runner scans /work directory after execution
- Uploads all outputs to MinIO: executions/&lt;exec_id&gt;/outputs/
- Records artifacts in database (filename, size, content_type)
- **Complexity:** Medium
- **Risk:** Low (MinIO SDK straightforward)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None (uses MinIO from Tier 4)
- **Tests:** Verify all output files uploaded, metadata recorded

**7-3: Store Outputs in MinIO with Retention Policy** (Epic 7)
- MinIO bucket: rgrid-executions
- Object lifecycle policy: 30-day retention
- Artifacts table tracks expiry date
- **Complexity:** Low
- **Risk:** Low (MinIO lifecycle feature)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 7-2
- **Tests:** Verify lifecycle policy applied, test expiry

---

#### Phase 2: Complete File Management (3 stories)
**Why second:** Full file workflow before batch operations

**7-1: Auto-Upload Input Files Referenced in Arguments** (Epic 7)
- Enhance Tier 1 basic version with full MinIO integration
- CLI detects files via os.path.isfile()
- Uploads to MinIO: executions/&lt;exec_id&gt;/inputs/
- Presigned PUT URLs for uploads
- **Complexity:** Medium
- **Risk:** Low (builds on 2-5)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 7-2
- **Tests:** Upload multiple files, verify in container

**7-4: Auto-Download Outputs to Current Directory (Single Execution)** (Epic 7)
- Enhance Tier 1 basic version with full MinIO downloads
- CLI downloads all outputs after execution completes
- Presigned GET URLs for downloads
- Parallel downloads for speed
- **Complexity:** Medium
- **Risk:** Low (MinIO SDK)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 7-2
- **Tests:** Verify files appear locally, handle missing files

**7-5: Implement --remote-only Flag to Skip Auto-Download** (Epic 7)
- CLI flag to skip automatic downloads
- Display command for manual download later
- **Complexity:** Low
- **Risk:** Low (simple flag)
- **Estimated effort:** 2-4 hours
- **Dependencies:** 7-4
- **Tests:** Verify no download when flag present

---

#### Phase 3: Batch Management (3 stories)
**Why third:** User-facing batch features (builds on 5-1, 5-2 from Tier 4.5)

**5-3: Track Batch Execution Progress** (Epic 5)
- Poll API for execution statuses
- Display: completed, failed, running, queued counts
- Calculate ETA based on average completion time
- Update every 2 seconds
- **Complexity:** Medium
- **Risk:** Low (polling logic)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 5-2
- **Tests:** Various batch sizes, verify accurate counts

**5-4: Organize Batch Outputs by Input Filename** (Epic 5)
- Create ./outputs/&lt;input-name&gt;/ directories
- Extract input filename from execution metadata
- Support --output-dir and --flat flags
- **Complexity:** Low
- **Risk:** Low (filesystem operations)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 5-3
- **Tests:** Verify directory structure, test flags

**5-5: Handle Batch Failures Gracefully** (Epic 5)
- Continue processing if some executions fail
- Collect failures in list
- Display final summary: "95 succeeded, 5 failed"
- Exit code = 0 if any succeeded, 1 if all failed
- **Complexity:** Medium
- **Risk:** Low (error collection)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 5-4
- **Tests:** Force failures, verify continued processing

---

#### Phase 4: Dependency Auto-Detection (1 story)
**Why fourth:** Enhances batch UX

**2-4: Auto-Detect and Install Python Dependencies** (Epic 2, deferred from Tier 3)
- Detect requirements.txt in script directory
- Install via `pip install -r requirements.txt`
- Cache installed packages for subsequent runs
- **Complexity:** Medium
- **Risk:** Medium (pip installation failures)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None (independent enhancement)
- **Tests:** Various requirements.txt files, verify installation

---

#### Phase 5: Caching System (3 stories)
**Why fifth:** Optimization after core features proven

**6-1: Implement Script Content Hashing and Cache Lookup** (Epic 6)
- Calculate script_hash = sha256(script_content)
- Check script_cache table for existing hash
- Skip Docker build if cache hit
- **Complexity:** Medium
- **Risk:** Low (hash calculation straightforward)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None
- **Tests:** Identical scripts use cache, modified scripts rebuild

**6-2: Implement Dependency Layer Caching** (Epic 6)
- Calculate deps_hash = sha256(requirements_content)
- Check dependency_cache table
- Use cached pip layer if hit
- Docker BuildKit integration for layer caching
- **Complexity:** High (upgraded from Medium - Docker layer caching is finicky)
- **Risk:** Medium (Docker layer management)
- **Estimated effort:** 10-14 hours (adjusted for BuildKit complexity)
- **Dependencies:** 6-1, 2-4
- **Tests:** Identical deps use cache, verify layer reuse, test invalidation

**6-3: Implement Automatic Cache Invalidation** (Epic 6)
- New hash calculated on script/deps change
- Cache lookup fails automatically
- New image built and cached with new hash
- **Complexity:** Low
- **Risk:** Low (implicit invalidation via hash change)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 6-2
- **Tests:** Modify script, verify cache miss and rebuild

---

#### Phase 6: Batch Retry (1 story)
**Why sixth:** Builds on both batch and caching

**5-6: Implement Retry for Failed Batch Executions** (Epic 5)
- API endpoint: POST /api/v1/executions/retry
- Retry only executions with status = failed
- Filter by batch_id + status=failed
- Retried executions get new execution IDs
- **Complexity:** Medium
- **Risk:** Low (database query + re-submit)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 5-5, 6-3
- **Tests:** Batch with failures, verify only failed retried

---

#### Phase 7: Optimizations (2 stories)
**Why last:** Performance enhancements after core works

**7-6: Implement Large File Streaming and Compression** (Epic 7)
- Stream files >100MB (not loaded into memory)
- Gzip compression for text files
- Multipart uploads (MinIO SDK)
- Auto-decompress on download
- **Complexity:** High
- **Risk:** Medium (streaming + compression coordination)
- **Estimated effort:** 8-12 hours
- **Dependencies:** 7-1, 7-4
- **Tests:** Upload/download 500MB files, verify streaming

**6-4: Implement Optional Input File Caching** (Epic 6)
- Calculate inputs_hash = sha256(all_input_contents)
- Check input_cache table
- Skip upload if cache hit
- **Complexity:** Medium
- **Risk:** Low (similar to 6-1)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 6-3, 7-6
- **Tests:** Reprocess same files, verify no re-upload

---

### Tier 5 Summary

**Total Stories:** 15
**Estimated Effort:** 86-122 hours (4-5 weeks, includes complexity adjustments)
**Critical Path:** 7-2 → 7-3 → 7-1 → 5-3 → 6-1 → 6-2

**Key Risks:**
1. **Batch coordination complexity** - Mitigation: Use battle-tested asyncio patterns
2. **Cache invalidation bugs** (CRITICAL from analyst review) - Mitigation: Comprehensive test matrix (2-3 days), all invalidation scenarios tested, cache observability instrumented
3. **Large file memory issues** - Mitigation: Streaming implementation, memory profiling, test with 1GB+ files
4. **Dependency installation failures** - Mitigation: Graceful error handling, fallback to base image
5. **Docker layer caching complexity** - Mitigation: BuildKit deep-dive, extensive testing of layer reuse

**Success Criteria:**
- ✅ Process 1000 CSV files in parallel across distributed workers
- ✅ Identical scripts execute instantly (cache hit)
- ✅ Batch progress visible in real-time
- ✅ Failed batch executions retry individually
- ✅ Large files (>500MB) upload/download without memory issues
- ✅ Dependencies auto-detected and installed from requirements.txt

**Testing Requirements:**
- **Unit tests:** Caching logic (hash calculation, lookup), 80%+ coverage
- **Integration tests:** 100+ file batches, end-to-end workflows
- **Load testing:** Large files (1GB+), memory profiling
- **Cache invalidation matrix** (2-3 days dedicated):
  - Script content changes
  - Dependency changes
  - Input file changes
  - Edge cases (zero-byte files, missing files, partial uploads)
- **Cache observability:** Instrument cache hit rate monitoring
- **Dependency installation:** Various requirements.txt files, failure scenarios
- **Documentation:** Batch execution tutorial with examples, caching behavior explained

---

## Tier 6: Production Polish & Interfaces

**Theme:** Observability, billing transparency, web interfaces, production-ready error handling

**Goal:** Complete MVP with user-facing interfaces, comprehensive observability, and transparent billing

**Value Delivered:**
- Real-time log streaming via WebSocket
- Transparent cost tracking and estimates
- Web console dashboard
- Marketing website
- Production-grade error handling and retry logic
- Execution metadata and tagging

### Prerequisites

- ✅ Tier 5 complete (all core features working)
- ✅ Batch execution operational
- ✅ Caching working
- ✅ File management complete

### Stories (14 total)

#### Phase 1: Observability Foundation (1 story)
**Why first:** Metadata needed for all observability and billing

**8-6: Track Execution Metadata in Database** (Epic 8)
- Record: execution_id, account_id, script_hash
- Track: start_time, end_time, duration_seconds
- Store: status, exit_code, worker_id, runtime, cost_micros
- Reference: input_files, output_files (artifact IDs)
- **Complexity:** Low
- **Risk:** Low (database schema enhancement)
- **Estimated effort:** 4-6 hours
- **Dependencies:** None (enhances existing executions table)
- **Tests:** Verify all metadata recorded correctly

---

#### Phase 2: Cost Tracking (2 stories)
**Why second:** Cost transparency is high-value, depends on metadata

**9-1: Implement MICRONS Cost Calculation** (Epic 9)
- MICRONS pattern: 1 EUR = 1,000,000 micros
- Calculate: cost_micros = (duration_seconds / 3600) * hourly_cost_micros
- Store as BIGINT in database
- Display to user as currency (e.g., €0.02)
- **Complexity:** Low
- **Risk:** Low (integer math)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 8-6
- **Tests:** Various durations, verify precision

**9-2: Implement Billing Hour Cost Amortization** (Epic 9)
- Two-phase costing: estimated → finalized
- Divide hourly cost among jobs when billing hour ends
- Update finalized_cost_micros for each execution
- **Complexity:** Medium
- **Risk:** Medium (time-based calculation)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 9-1
- **Tests:** Multiple jobs in billing hour, verify fair distribution

---

#### Phase 3: Real-Time Streaming (2 stories)
**Why third:** Real-time feedback is high-value feature

**8-3: Implement WebSocket Log Streaming for Real-Time Logs** (Epic 8)
- WebSocket endpoint: /api/v1/executions/{exec_id}/stream
- Runner → API → CLI log pipeline
- Real-time logs (< 1 second latency)
- Stream until execution completes or user cancels
- **Complexity:** High
- **Risk:** High (WebSocket state management)
- **Estimated effort:** 10-14 hours
- **Dependencies:** None (independent feature)
- **Tests:** Long-running jobs, verify real-time streaming

**8-4: Implement CLI Reconnection for WebSocket Streams** (Epic 8)
- Detect WebSocket disconnection
- Auto-reconnect within 5 seconds
- Resume from last log line (cursor-based)
- Exponential backoff for retry
- **Complexity:** High
- **Risk:** Medium (reconnection edge cases)
- **Estimated effort:** 8-12 hours
- **Dependencies:** 8-3
- **Tests:** Force disconnects, verify seamless resumption

---

#### Phase 4: Batch Progress Display (1 story)
**Why fourth:** Builds on WebSocket streaming

**8-5: Implement Batch Progress Display with --watch** (Epic 8)
- Aggregate progress from multiple executions
- Display: completed, failed, running, queued counts
- Calculate ETA based on average completion time
- Interactive: press 'l' for logs, 'q' to detach
- **Complexity:** High
- **Risk:** Medium (UI state management)
- **Estimated effort:** 8-12 hours
- **Dependencies:** 5-3, 8-3
- **Tests:** Large batches, verify accurate progress

---

#### Phase 5: Cost Commands (2 stories)
**Why fifth:** User-facing cost features after calculation works

**9-3: Implement `rgrid cost` Command** (Epic 9)
- Display: date, executions, compute time, cost
- Support date range filtering: --since, --until
- API endpoint: GET /api/v1/costs
- **Complexity:** Low
- **Risk:** Low (database query + formatting)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 9-2
- **Tests:** Various date ranges, verify accuracy

**9-4: Implement Cost Estimation for Batch Executions** (Epic 9)
- Estimate based on historical data
- Calculate: (count * avg_duration * hourly_cost) / 3600
- Display before batch execution starts
- **Complexity:** Medium
- **Risk:** Low (estimation algorithm)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 9-3
- **Tests:** Verify estimates reasonable, compare to actuals

---

#### Phase 6: Error Handling & Retry (4 stories)
**Why sixth:** Production reliability features

**10-4: Implement Structured Error Handling with Clear Messages** (Epic 10)
- Detect common errors: missing deps, syntax errors, timeouts
- Map to actionable messages
- Display cause and fix suggestions
- **Complexity:** Medium
- **Risk:** Low (error detection patterns)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None (enhances existing error handling)
- **Tests:** Trigger various errors, verify messages

**10-5: Implement Network Failure Graceful Handling** (Epic 10)
- Auto-retry with exponential backoff
- Max 5 retry attempts
- Display: "Connection lost. Retrying... (attempt 2/5)"
- **Complexity:** Medium
- **Risk:** Low (httpx retry logic)
- **Estimated effort:** 4-6 hours
- **Dependencies:** None (CLI enhancement)
- **Tests:** Force network failures, verify retries

**10-6: Implement Manual Retry Command** (Epic 10)
- API endpoint: POST /api/v1/executions/{exec_id}/retry
- Clone execution record with new ID
- CLI command: `rgrid retry exec_abc123`
- **Complexity:** Low
- **Risk:** Low (duplicate execution)
- **Estimated effort:** 4-6 hours
- **Dependencies:** None
- **Tests:** Retry failed executions, verify new exec_id

**10-7: Implement Auto-Retry for Transient Failures** (Epic 10)
- Detect transient errors: worker died, network timeout
- Auto-retry max 2 times
- Track retry count in metadata
- Don't retry: script errors, validation errors
- **Complexity:** Medium
- **Risk:** Medium (failure classification)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 10-6
- **Tests:** Simulate transient failures, verify auto-retry

---

#### Phase 7: Metadata Tagging (1 story)
**Why seventh:** Organizational feature builds on metadata foundation

**10-8: Implement Execution Metadata Tagging** (Epic 10)
- CLI flag: --metadata key=value
- Store as JSONB column in executions table
- Filter via: `rgrid list --metadata project=ml-model`
- **Complexity:** Low
- **Risk:** Low (JSONB column)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 8-6
- **Tests:** Tag executions, query by metadata

---

#### Phase 8: Web Interfaces (2 stories)
**Why eighth:** User-facing interfaces after all features work

**10-1: Build Marketing Website Landing Page** (Epic 10)
- Next.js 14 static site (App Router)
- Deploy to Vercel or control plane
- Hero: "Run Python scripts remotely. No infrastructure."
- CTA: "Get Started" → https://app.rgrid.dev/signup
- **Complexity:** Low
- **Risk:** Low (static website)
- **Estimated effort:** 6-8 hours
- **Dependencies:** None
- **Tests:** Manual review, performance testing

**10-2: Build Console Dashboard with Execution History** (Epic 10)
- Next.js 14 dashboard (App Router)
- Clerk authentication
- Table: execution_id, script_name, status, started_at, duration, cost
- Click execution → detail view with logs
- **Complexity:** Medium
- **Risk:** Low (CRUD interface)
- **Estimated effort:** 10-14 hours
- **Dependencies:** 8-6
- **Tests:** Manual testing, verify all features

---

#### Phase 9: Console Features (1 story)
**Why ninth:** Console enhancement after dashboard exists

**10-3: Implement Download Outputs via Console** (Epic 10)
- List output files with sizes
- Generate presigned GET URLs server-side
- Click "Download" to retrieve file
- **Complexity:** Low
- **Risk:** Low (builds on existing download logic)
- **Estimated effort:** 4-6 hours
- **Dependencies:** 10-2
- **Tests:** Download various file types, verify presigned URLs

---

#### Phase 10: Future Enhancement (1 story)
**Why last:** Optional feature, may defer to post-MVP

**9-5: Implement Cost Alerts (Future Enhancement)** (Epic 9)
- Set spending limits: `rgrid cost set-limit €50/month`
- Email alerts at 80% of limit
- Block executions at 100%
- **Complexity:** Medium
- **Risk:** Low (threshold checking)
- **Estimated effort:** 6-8 hours
- **Dependencies:** 9-3
- **Priority:** OPTIONAL - May defer to post-Tier 6
- **Tests:** Various limits, verify alerts trigger

---

### Tier 6 Summary

**Total Stories:** 14
**Estimated Effort:** 86-124 hours (3-4 weeks)
**Critical Path:** 8-6 → 9-1 → 9-2 → 8-3 → 10-2

**Key Risks:**
1. **WebSocket state management** - Mitigation: Use battle-tested libraries (FastAPI WebSocket), extensive reconnection testing
2. **WebSocket connection scaling** (NEW from analyst review) - Mitigation: Load testing BEFORE Tier 6, FastAPI default won't scale past ~100 concurrent connections; Consider Redis pub/sub for scaling
3. **Cost calculation precision** - Mitigation: MICRONS pattern (integer math), comprehensive test coverage, no floating point
4. **Web console authentication** - Mitigation: Clerk integration (already in architecture), implement proper API key auth BEFORE Tier 6
5. **Real-time streaming performance** - Mitigation: Load testing with 100+ concurrent streams, connection pooling

**Success Criteria:**
- ✅ Real-time logs stream with <1s latency
- ✅ Cost displayed accurately for all executions
- ✅ Web console shows execution history and logs
- ✅ Marketing website deployed and accessible
- ✅ Error messages actionable and user-friendly
- ✅ Transient failures auto-retry successfully
- ✅ Execution metadata queryable and filterable

**Testing Requirements:**
- **WebSocket load tests:** 100+ concurrent connections, measure latency and throughput
- **WebSocket scaling research:** Test connection limits, evaluate Redis pub/sub if needed
- **Cost calculation precision:** Various durations, verify MICRONS math, no rounding errors
- **Web console:** UI/UX testing, authentication flows, all features functional
- **Error message review:** User testing for clarity, ensure actionable guidance
- **Retry logic:** Failure injection for transient vs permanent failures
- **Metadata querying:** Performance tests with 10,000+ executions
- **Documentation:** Web console user guide, video walkthrough, cost transparency docs

---

## Cross-Tier Considerations

### Technical Debt to Address

1. **Simplified Auth (from Tier 1)**
   - Current: Accepts any `sk_*` format key
   - Fix: Implement proper API key hashing and database lookup
   - **When:** Before Tier 6 (10-2 needs real auth for console)
   - **Estimated effort:** 4-6 hours

2. **Stderr Separation (from Tier 2)**
   - Current: Docker merges stderr into stdout
   - Fix: Capture stderr separately in DockerExecutor
   - **When:** Tier 5 or 6 (nice-to-have)
   - **Estimated effort:** 2-4 hours

3. **Output Size Limits (from Tier 2)**
   - Current: 100KB limit with truncation
   - Fix: Stream large outputs to MinIO
   - **When:** Tier 5 (7-6 addresses this)
   - **Estimated effort:** Included in 7-6

### Testing Strategy

**Per-Tier Testing:**
- Unit tests for all new functions/classes (80%+ coverage)
- Integration tests for new features (key workflows)
- Manual testing for user-facing changes
- Pre-commit hook runs all tests before commit

**Cross-Tier Testing:**
- Load testing after Tier 4 (distributed execution)
- End-to-end batch testing after Tier 5
- Performance testing after Tier 6 (WebSocket scaling)

**Production Readiness:**
- Tier 4: Distributed execution functional
- Tier 5: Data processing workloads ready
- Tier 6: Full MVP ready for public release

### Deployment Considerations

**Tier 4 Deployment:**
- Deploy Ray head node to control plane
- Configure Hetzner API credentials
- Set up private networking for workers
- Test with real Hetzner provisioning

**Tier 5 Deployment:**
- Configure MinIO lifecycle policies
- Increase database storage for artifacts
- Monitor cache hit rates
- Benchmark batch performance

**Tier 6 Deployment:**
- Deploy web console and marketing website
- Configure Clerk authentication
- Set up email alerts for cost limits
- Monitor WebSocket connection limits

---

## Implementation Timeline

### Aggressive Schedule (Full-Time)

- **Tier 4:** 4 weeks (distributed execution & cloud infrastructure)
- **Security Review:** 1 week (MANDATORY security audit)
- **Tier 4.5:** 1 week (batch quick win)
- **Tier 5:** 4 weeks (batch management, caching, file optimization)
- **Tier 6:** 4 weeks (observability, billing, web interfaces)
- **Total:** 14 weeks (70 work days)

### Moderate Schedule (Part-Time or with Unknowns)

- **Tier 4:** 5 weeks (account for Ray/Hetzner complexity, chaos testing)
- **Security Review:** 1 week (security audit, pen testing)
- **Tier 4.5:** 1 week (batch execution basics)
- **Tier 5:** 5 weeks (account for caching edge cases, cache testing)
- **Tier 6:** 5 weeks (account for WebSocket testing, web console UX)
- **Total:** 17 weeks

### Recommended Approach

**Iterative Delivery:**
1. Complete Tier 4, deploy to staging, test thoroughly
2. Run retrospective, adjust Tier 5 plan
3. Complete Tier 5, deploy to staging, load test
4. Run retrospective, adjust Tier 6 plan
5. Complete Tier 6, deploy to production

**Milestones:**
- **End of Tier 4:** Distributed execution functional (infrastructure demo)
- **After Security Review:** Security audit complete, ready for user code
- **End of Tier 4.5:** Batch execution demo ("process 1000 CSVs across cloud workers")
- **End of Tier 5:** Advanced batch + caching demo (instant re-runs)
- **End of Tier 6:** Public MVP release with web console

---

## Risk Mitigation

### High-Risk Areas

1. **Ray Cluster Networking (Tier 4)**
   - **Risk:** Workers can't connect to head node
   - **Mitigation:** Test locally with Docker Compose Ray cluster first
   - **Fallback:** Simplify to direct API polling (no Ray)

2. **Hetzner Provisioning (Tier 4)**
   - **Risk:** API failures, rate limits, networking issues
   - **Mitigation:** Extensive error handling, retry logic, monitoring
   - **Fallback:** Manual worker provisioning for pilot

3. **WebSocket Scaling (Tier 6)**
   - **Risk:** Too many concurrent connections crash API
   - **Mitigation:** Connection limits, load balancing, monitoring
   - **Fallback:** Poll-based log retrieval (no WebSocket)

4. **Cost Calculation Precision (Tier 6)**
   - **Risk:** Rounding errors, billing discrepancies
   - **Mitigation:** MICRONS pattern (integer math), comprehensive tests
   - **Fallback:** Manual billing reconciliation

### Contingency Plans

**If Tier 4 Takes Too Long:**
- Implement simplified provisioning (no billing hour optimization)
- Defer worker auto-replacement (manual cleanup)
- Proceed to Tier 5 with single-worker scaling

**If Tier 5 Caching is Complex:**
- Defer caching to post-MVP
- Focus on batch execution (higher user value)
- Accept slower repeat executions

**If Tier 6 WebSocket is Problematic:**
- Use polling for log retrieval (acceptable latency)
- Defer real-time streaming to post-MVP
- Ensure historical logs work perfectly

---

## Success Metrics

### Tier 4 Success Metrics

- Worker provisioning time: < 90 seconds
- Dead worker detection time: < 3 minutes
- Job distribution across 10+ workers: even load
- Cost per execution: < €0.01 for 5-minute job

### Tier 5 Success Metrics

- Batch processing throughput: 100+ jobs/minute
- Cache hit rate: >80% for repeated executions
- Large file upload/download: 100MB in <60 seconds
- Dependency installation success rate: >95%

### Tier 6 Success Metrics

- WebSocket log latency: <1 second
- Cost calculation accuracy: 100%
- Web console load time: <2 seconds
- Error message clarity: 90% user satisfaction
- Retry success rate for transient failures: >90%

---

## Conclusion

This roadmap provides a clear, dependency-aware path from the current production-ready single-node system (Tier 3) to a fully-featured, horizontally-scaled, production-grade MVP (Tier 6).

**Key Principles:**
1. **Incremental Value:** Each tier delivers complete, usable features
2. **Risk Management:** High-risk stories tackled early with fallback plans
3. **Technical Coherence:** Dependencies respected, no forward references
4. **Testability:** Comprehensive testing at each tier
5. **Pragmatism:** Focus on boring technology that works

**Next Steps:**
1. Review and approve this roadmap
2. Create Tier 4 implementation plan
3. Set up Tier 4 testing environment (Ray + Hetzner sandbox)
4. Begin Tier 4 Phase 1: File Handling Foundation

---

**Document Status:** Revised after Multi-Agent Review (2025-11-15)
**Estimated Total Effort:** 308-428 hours (14-17 weeks)
**MVP Target:** Tier 6 Complete
**Production Release:** After Tier 6 + Load Testing + Security Audit

**Revisions Applied:**
- ✅ Effort estimates adjusted +20-30% for high complexity stories (Amelia/Developer review)
- ✅ Tier 4.5 added for immediate user value (John/PM + Bob/SM recommendation)
- ✅ Security Review milestone added (Mary/Analyst recommendation)
- ✅ Missing risks identified and documented (Mary/Analyst review)
- ✅ Testing requirements enhanced (Murat/TEA review - chaos engineering, baselines, cache observability)
- ✅ DX improvements added (Sally/UX Designer - provisioning feedback, error messages)
- ✅ Documentation deliverables added to each tier (Paige/Tech Writer recommendation)

**Key Changes from Party Mode Review:**
1. Story count: 44 → 46 stories (added NEW-4 provisioning feedback, kept 5-1/5-2 separate)
2. Timeline: 10-13 weeks → 14-17 weeks (more realistic with complexity buffer)
3. Structure: 3 tiers → 4 milestones (Tier 4, Security Review, Tier 4.5, Tier 5, Tier 6)
4. Risks: Added Hetzner limits, cache invalidation criticality, WebSocket scaling
5. Testing: Added chaos engineering, baseline metrics, cache testing matrix
6. Value delivery: Tier 4.5 creates natural demo point after infrastructure

Good engineering is about making the complex simple and the simple boring. Let's build something reliable.

🏗️ **Winston - System Architect**
🎉 **With input from the entire BMAD party**
