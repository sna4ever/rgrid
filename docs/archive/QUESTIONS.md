# RGrid - Critical Clarification Questions

This document captures questions that need clarification to finalize the architecture and implementation.

**Legend:**
- ✅ **ANSWERED** (from chatlog.md)
- ❓ **NEEDS CLARIFICATION** (partial info or conflicting details)
- ⚠️ **PHASE 4 FEATURE** (deferred to later)

---

## Questions & Answers

### 1. Input File Ownership & Presigned URL Generation ✅

**Question:** JOB_SPEC.md shows inputs with `"url": "<PRESIGNED-GET-URL>"` but doesn't specify who generates these URLs.

**Answer from chatlog:**
- Users provide their own presigned URLs from their existing S3 buckets (chatlog line 5360: "You already have all PNGs in s3://my-bucket/images/…")
- Users reference external storage URLs in `files.inputs[]` (line 5363: "each job references its input file via an HTTPS or S3 presigned URL")
- Example shows: `{"path": "input.mp4", "url": "https://storage.rgrid.dev/tmp/xyz.mp4"}` (line 4307)

**CONFIRMED DECISION:**
- ✅ RGrid provides a `POST /projects/:slug/files/upload` endpoint
- ✅ Users can upload files to RGrid-managed MinIO and receive presigned GET URLs
- ✅ Users can also provide their own S3/storage URLs (BYO storage)
- ✅ Both workflows supported: RGrid-managed storage (MVP) + BYO storage (optional)

**Implementation:** API endpoint returns presigned GET URL with ~30-120 min expiry for downloaded inputs.

---

### 2. Inline Python Code Execution Model ✅

**Question:** How does inline Python code execution work?

**Answer from chatlog:**
- ✅ Runner writes inline code to `/app/main.py` (line 7183, 9241)
- ✅ User specifies runtime image like `"runtime": "python:3.11-slim"` (line 4194, 4250)
- ✅ Requirements installed via: `pip install -r requirements.txt && python main.py` (line 3904)
- ✅ Command is typically `["python", "main.py"]` (line 4014, 7167)

**Process:**
1. Runner creates `/work/<job_id>/` directory
2. If `spec.code` exists, writes to `/work/<job_id>/main.py`
3. If `spec.requirements` exists, creates `requirements.txt`
4. Container runs: `pip install -r requirements.txt && python main.py`

**Confirmed:** This is well-defined in chatlog.

---

### 3. CPU Resource Allocation & Node Packing ✅

**Question:** How are jobs packed onto nodes with 2 vCPUs?

**Answer from chatlog:**
- ✅ **Strict policy: 1 job per vCPU** (line 6111, 6224, 6272, 6430, 6783)
- ✅ CX22 has 2 vCPUs → can run 2 concurrent jobs (line 6783, 6430)
- ✅ CPU value in JobSpec is a **hard limit** applied via Docker `--cpus` flag (line 1993, 5159)

**Confirmed:** Maximum 2 concurrent jobs per CX22 node, regardless of individual job CPU requests. This simplifies scheduling and ensures predictable performance.

---

### 4. Multi-Project Node Sharing ✅

**Question:** Do nodes claim jobs from multiple projects or are they dedicated per project?

**Answer from chatlog:**
- Chatlog shows `WHERE project_id = $1` in claim query (line 4814, 7784)
- Orchestrator monitors "queue depth per project" (line 8160)
- Mentions "node pools per project" (line 7045, 10196)

**CONFIRMED DECISION:**
- ✅ **Shared pool architecture** - this is the core business value proposition
- ✅ Nodes are NOT dedicated per project
- ✅ Nodes claim jobs from ANY project (cross-project job execution)
- ✅ Enables efficient resource utilization and cost savings

**Implementation notes:**
- Orchestrator aggregates queue depth across ALL projects to determine node count
- Claim logic should be `WHERE status = 'queued' ORDER BY priority, created_at` (remove project_id filter)
- Fair scheduling achieved through FIFO queue ordering (can add priority/weights later)
- Account-level isolation maintained through DB row-level security and MinIO bucket policies

---

### 5. API Key Scoping & Permissions ✅

**Question:** What is the scope and permission model for API keys?

**Answer from chatlog:**
- ✅ API keys are **scoped per project** (line 334, 370, 1294, 5041)
- ✅ API key grants **full project access** but **not account access** (line 9767, 9769, 9770)
- ✅ Separate from user roles (owner/admin/developer/viewer)

**Confirmed:** One API key per project. Cannot access multiple projects or account-level operations.

---

### 6. Runner Authentication & Node Identity ✅

**Question:** How do newly spawned nodes authenticate with the API?

**Answer from chatlog:**
- ✅ Node token generated at spawn time (line 9816: "node token generated at spawn")
- ✅ Node registration endpoint: `POST /runner/register` (line 9617)
- ✅ Cloud-init script includes bootstrap process (line 6968-6972, 7762-7763)
- ✅ Node tokens allow runner API access (line 9820)

**Process:**
1. Orchestrator spawns node with cloud-init script containing bootstrap token
2. Cloud-init installs Docker + rgrid-runner binary
3. Runner calls `POST /runner/register` with bootstrap token
4. API generates long-lived node token
5. Runner uses node token for all subsequent API calls (claim, heartbeat, finish)

**Confirmed:** Bootstrap token in cloud-init enables initial registration, then node token for ongoing operations.

---

### 7. Failure vs. Abandoned Job Classification ✅

**Question:** What's the distinction between failed and abandoned jobs?

**Answer from chatlog:**
- ✅ **Failed:** Non-zero exit code from container (line 2009, 3633, 3908, 4605, 6411, 7523)
- ✅ **Abandoned:** Heartbeat timeout / node death (line 3280: "Requeue stuck jobs (heartbeat timeout)")
- ✅ Max retries: Default 2 (line 4262, 4577, 7491)
- ✅ Retry condition: `retries < max_retries` (line 4765, 4768, 7652)

**Retry logic:**
- Failed jobs (exit code != 0): Increment `retries`, set status back to `queued` if `retries < max_retries`
- Abandoned jobs (heartbeat timeout): Same retry logic
- Both use the same retry mechanism

**Confirmed:** Clear distinction and unified retry policy.

---

### 8. Network-Enabled Jobs Policy ✅

**Question:** How do jobs opt-in to network access?

**Answer from chatlog:**
- ✅ Default: `"network": false` → `--network=none` (line 4033, 4067, 4232, 4261, 7121, 9192)
- ✅ Opt-in via JobSpec: `"network": true`
- ✅ Future: Optional egress allow-list via proxy container (line 1992: "optional egress allow-list via a jump/proxy container")

**CONFIRMED DECISION:**
- ✅ **No restrictions on runtime images** - any image can use `network: true`
- ✅ Simple boolean flag in JobSpec controls network access
- ✅ MVP: User-controlled via JobSpec field only
- ✅ Phase 3: Add project-level policies, egress filtering, allowlists

**Implementation:** Runner checks `spec.network` boolean and omits `--network=none` flag when true.

---

### 9. MinIO Multi-Tenancy Architecture ✅

**Question:** What is the bucket structure for multi-tenancy?

**Answer from chatlog:**
- ✅ **Single bucket with path-based isolation:** `artifacts/<account>/<project>/<job>/<filename>` (line 9046, 10328)
- ✅ MinIO bucket policies enforce isolation (line 8880, 9074, 9843)
- ✅ Presigned URLs scoped to specific paths ensure tenant isolation

**Confirmed:** One bucket (`rgrid-artifacts`) with hierarchical prefixes and bucket policies. Simpler than per-tenant buckets.

---

### 10. Orchestrator Scaling Strategy ✅

**Question:** Does the orchestrator maintain per-project node pools or a shared pool?

**Answer from chatlog:**
- Orchestrator monitors queue depth (line 6561, 8160)
- Spawns nodes based on queue depth (line 6429, 8143, 8165)
- Scaling formula: `desired_nodes = ceil(queued_jobs / vCPUs_per_node)` (from docs)

**CONFIRMED DECISION:**
- ✅ **Global shared pool** (same as Question 4)
- ✅ Nodes are NOT tagged with project_id
- ✅ Any node can claim any job from any project
- ✅ Autoscaling based on **total queue depth across all projects**

**Scaling formula:**
```
total_queued = COUNT(*) FROM jobs WHERE status = 'queued'
desired_nodes = ceil(total_queued / 2)  # 2 jobs per CX22 node
```

**Benefits:**
- Maximum resource utilization (no idle nodes waiting for specific project)
- Cost efficiency - shared infrastructure scales with total demand
- Simpler orchestrator logic - single scaling decision

---

## Summary - ALL QUESTIONS RESOLVED ✅

### Core Architecture Decisions (MVP):

1. ✅ **Input files:** RGrid provides `POST /projects/:slug/files/upload` endpoint + supports BYO storage
2. ✅ **Node pooling:** Global shared pool - any node claims jobs from any project (core business value)
3. ✅ **Inline Python:** Code written to `/app/main.py`, requirements installed via pip
4. ✅ **CPU allocation:** Strict 1 job per vCPU (max 2 concurrent jobs per CX22 node)
5. ✅ **API keys:** Scoped per project, full project access only
6. ✅ **Node auth:** Bootstrap token → node token flow via `POST /runner/register`
7. ✅ **Job failures:** Failed (exit code) vs Abandoned (heartbeat timeout), max 2 retries
8. ✅ **Network access:** Simple `network: true/false` flag, no image restrictions
9. ✅ **MinIO tenancy:** Single bucket with path `artifacts/<account>/<project>/<job>/<file>`
10. ✅ **Autoscaling:** Global pool, scale on total queue depth: `ceil(total_queued / 2)`

### Phase 2/3 Enhancements:

- Egress filtering and allow-lists for network-enabled jobs
- Advanced fair scheduling (priority, weights, quotas)
- Cross-account cost tracking and billing
- GPU node support

---

## Status
- **Created:** 2025-11-14
- **Updated:** 2025-11-14 - All questions resolved
- **Source:** Documentation review + chatlog.md analysis + project owner decisions
- **Next Steps:** Update documentation to reflect shared pool architecture and upload endpoint
