# RGrid Architecture Summary

**Status:** ✅ Architecture Complete - Ready for Implementation
**Date:** 2025-11-15
**Track:** BMad Method - Greenfield
**Full Document:** [architecture.md](./architecture.md)

---

## 🎯 Architecture Completed

All 12 critical architectural decisions have been finalized and documented. The complete architecture document is ready for implementation.

## 📋 Decisions Overview

### ✅ Decision 1: Project Structure
- **Chosen:** Monorepo with shared Python package
- **Structure:** `api/`, `orchestrator/`, `runner/`, `website/`, `console/`, `cli/`, `common/`, `infra/`
- **Distribution:** CLI via PyPI, services via Docker images, web apps via Next.js
- **Web Apps:** Marketing website (rgrid.dev) + Console dashboard (app.rgrid.dev)

### ✅ Decision 2: Database Schema
- **Pattern:** Jumpstart-style multi-tenant (Accounts → Users → Memberships)
- **Cost Tracking:** MICRONS (BIGINT) - 1 EUR = 1,000,000 microns
- **Workers:** Shared pool across all accounts (not siloed)
- **Billing:** Hourly optimization with cost finalization
- **Key Tables:** 21 tables including accounts, executions, workers, ray_jobs, artifacts

### ✅ Decision 3: Ray Cluster Architecture
- **Head Node:** Separate container on control plane
- **Worker Discovery:** Hardcoded control plane IP (10.0.0.1:6379)
- **Object Store:** Ray head node manages object store

### ✅ Decision 4: Docker Image Management
- **Registry:** MinIO-backed local registry
- **Build Location:** Control plane
- **Optimization:** Multi-stage builds, layer caching, base image preloading

### ✅ Decision 5: File Upload/Download
- **Small Files (<10MB):** Direct via API (base64 or multipart)
- **Large Files (>10MB):** Presigned MinIO URLs (direct upload/download)
- **Artifacts:** Always handled by Runner (not inside container)

### ✅ Decision 6: Authentication
- **Web/Console:** Clerk OIDC (users authenticate via web)
- **CLI:** API Keys (AWS credential pattern via `~/.rgrid/credentials`)
- **Multi-User:** Account memberships support multiple users per account

### ✅ Decision 7: API Route Structure (LLM-Agent Friendly)
- **Folder Structure:** Stable, predictable (`/api/routes/`, `/api/services/`, `/api/schemas/`)
- **Pydantic Everywhere:** All requests/responses use Pydantic models
- **Pure Service Functions:** Business logic separated from HTTP handlers
- **Explicit Types:** SQLAlchemy models with explicit column types
- **OpenAPI Documentation:** Comprehensive tags, descriptions, examples
- **Error Handling:** Deterministic error codes and structured responses

### ✅ Decision 8: WebSocket Implementation
- **Real-Time Logs:** WebSocket streaming with line-by-line updates
- **Fallback:** HTTP polling for environments without WS support
- **Reconnection:** Automatic reconnect with cursor-based resumption
- **Format:** Structured JSON with timestamps and correlation IDs

### ✅ Decision 9: Worker Provisioning Logic
- **Strategy:** Queue-based smart provisioning
- **Utilization First:** Don't provision if existing workers can handle queue
- **Billing Hour Aware:** Keep workers until billing hour ends
- **Cost Amortization:** Distribute hourly cost across all jobs in billing hour
- **Algorithm:**
  ```
  queued_jobs = count(status='queued')
  available_slots = sum(worker.max_concurrent for idle workers)
  est_completion_time = estimate_current_jobs()

  if available_slots >= queued_jobs:
      provision = 0
  elif est_completion_time < 5 minutes:
      provision = 0  # Jobs will complete soon
  else:
      provision = ceil((queued_jobs - available_slots) / 2)  # CX22 has 2 slots
  ```

### ✅ Decision 10: Content-Hash Caching
- **Three Levels:**
  1. **Script Cache:** SHA256 of script content
  2. **Dependency Cache:** SHA256 of requirements.txt content
  3. **Input Cache:** SHA256 of all input file contents
- **Composite Key:** `script_hash + deps_hash + inputs_hash`
- **Benefits:** Avoid re-execution of identical jobs, instant results for cache hits
- **Storage:** Ray object store for cached results

### ✅ Decision 11: Error Handling Strategy
- **Consistent Error Codes:**
  - `VALIDATION_ERROR` - Invalid input
  - `INSUFFICIENT_CREDITS` - Account balance too low
  - `RESOURCE_NOT_FOUND` - Job/artifact not found
  - `EXECUTION_TIMEOUT` - Job exceeded time limit
  - `EXECUTION_FAILED` - Job crashed/errored
  - `RATE_LIMIT_EXCEEDED` - Too many requests
- **ErrorResponse Model:** Structured Pydantic model with code, message, details
- **Retries:** Automatic retry for transient failures (3 attempts)
- **Idempotency:** All POST operations idempotent via execution_id

### ✅ Decision 12: Logging Format
- **Format:** Structured JSON (not plaintext)
- **Fields:**
  ```json
  {
    "timestamp": "2025-11-15T10:30:45.123Z",
    "level": "INFO",
    "correlation_id": "exec_abc123",
    "component": "runner",
    "message": "Job started",
    "execution_id": "exec_abc123",
    "worker_id": "worker_xyz789",
    "account_id": "acct_123"
  }
  ```
- **Correlation IDs:** Track request across all components
- **Centralized:** All logs stored in MinIO for analysis
- **Retention:** 30 days for all logs

---

## 🏗️ Key Architectural Patterns

### MICRONS for Cost Tracking
```python
class Money:
    """
    All costs stored as BIGINT micros in database.
    1 EUR/USD = 1,000,000 micros
    1 cent = 10,000 micros
    """
    MICROS_PER_UNIT = 1_000_000

    def __init__(self, micros: int, currency: str = 'EUR'):
        self.micros = int(micros)  # Always integer!
        self.currency = currency.upper()
```

**Why?** Exact integer math, no float imprecision, perfect for tiny costs (€0.000001/second).

### Shared Worker Pool
- Workers are **NOT** scoped to accounts
- All workers serve all accounts (shared pool)
- Maximizes utilization across entire fleet
- Billing hour optimization distributes costs

### Billing Hour Optimization
```python
# Worker lifecycle
worker.billing_hour_start = datetime.utcnow()
worker.billing_hour_end = worker.billing_hour_start + timedelta(hours=1)

# Don't terminate until hour ends
if datetime.utcnow() < worker.billing_hour_end:
    keep_worker_alive()  # Maximize utilization
else:
    terminate_worker()
```

**Why?** Hetzner bills hourly. Keep workers until hour ends, amortize costs across all jobs.

### Cost Finalization (Two-Phase)
1. **Estimated Cost (Immediate):** Charge account based on estimated runtime
2. **Finalized Cost (After Billing Hour):** Recalculate with actual amortization

```python
# Estimated (job start)
job.estimated_cost_micros = worker.hourly_cost_micros * (estimated_seconds / 3600)

# Finalized (billing hour end)
jobs_in_hour = worker.jobs.filter(billing_hour=worker.current_billing_hour)
cost_per_job = worker.hourly_cost_micros / len(jobs_in_hour)
job.finalized_cost_micros = cost_per_job
```

### LLM-Agent Friendly Code
**10 Principles Applied Throughout:**
1. ✅ Stable folder structure
2. ✅ Pydantic schemas everywhere
3. ✅ OpenAPI tags/descriptions
4. ✅ Pure functions in service layer
5. ✅ Docstrings everywhere
6. ✅ Deterministic error messages
7. ✅ Factory functions/templates
8. ✅ Explicit SQLAlchemy types
9. ✅ Sandbox tests
10. ✅ Idempotent operations

**Example:**
```python
# THIN route handler
@router.post("", response_model=Execution, status_code=201)
async def create_execution(
    execution_data: ExecutionCreate,
    account: Account = Depends(get_authenticated_account)
):
    """Create execution. THIN handler - logic in service layer."""
    return await execution_service.create(db, account, execution_data)

# PURE service function (no HTTP concerns)
async def create(
    db: AsyncSession,
    account: Account,
    execution_data: ExecutionCreate
) -> Execution:
    """Create execution. PURE FUNCTION - no HTTP concerns."""
    # Business logic only
    ...
```

---

## 🗄️ Database Schema Highlights

**21 Tables** organized into logical groups:

### Multi-Tenancy (Jumpstart Pattern)
- `accounts` - Billing entity (has credits)
- `users` - Individual humans (Clerk-synced)
- `account_memberships` - Many-to-many join table

### Execution & Jobs
- `executions` - User-facing job submissions
- `ray_jobs` - Ray framework jobs (1:1 with executions)
- `artifacts` - Output files from jobs
- `execution_logs` - Structured log entries

### Workers & Infrastructure
- `workers` - Physical Hetzner servers
- `server_types` - Data-driven server configurations (CX22, etc.)
- `worker_heartbeats` - Liveness tracking

### Billing & Credits
- `account_credits` - Credit transactions (purchases, usage)
- `payments` - Stripe payment records
- `usage_records` - Aggregated monthly usage

### Caching
- `script_cache` - Cached script executions
- `dependency_cache` - Cached pip packages
- `input_cache` - Cached input file combinations

### Configuration
- `api_keys` - CLI authentication
- `webhooks` - Event delivery endpoints

**Key Schema Patterns:**
- All IDs use `prefix_id` (e.g., `exec_abc123`, `acct_456xyz`)
- All costs stored as `BIGINT` (micros)
- All timestamps `TIMESTAMPTZ` (UTC)
- Indexes on `account_id`, `status`, `created_at`
- Foreign keys with `ON DELETE` constraints

---

## 🚀 Deployment Architecture (Hetzner All-In-One)

### Control Plane: Hetzner CX31 (€10.49/month)
- **Specs:** 2 vCPU, 8GB RAM, 80GB NVMe
- **Services:**
  - FastAPI (API server)
  - Marketing Website (Next.js)
  - Console Dashboard (Next.js)
  - PostgreSQL (job queue, metadata)
  - MinIO (S3-compatible storage)
  - Ray Head Node (cluster coordinator)
  - Local Docker Registry (image caching)
  - Nginx (reverse proxy)
- **Domains:**
  - `rgrid.dev` → Marketing website
  - `app.rgrid.dev` → Console dashboard
  - `api.rgrid.dev` → FastAPI backend
- **Private Network:** 10.0.0.0/16 (control plane at 10.0.0.1)

### Workers: Hetzner CX22 (€5.83/month each, ephemeral)
- **Specs:** 2 vCPU, 4GB RAM, 40GB NVMe
- **Provisioning:** On-demand via cloud-init
- **Ray Worker:** Joins cluster at 10.0.0.1:6379
- **Max Concurrent:** 2 jobs (1 job per vCPU)
- **Lifetime:** ~60 minutes (billing hour optimization)

### Total MVP Cost
- **Fixed:** €10.49/month (control plane)
- **Variable:** €5.83/hour per worker (only when needed)
- **Example:** 10 jobs/hour = ~€0.97/hour for workers

---

## 🔐 Security Architecture

### Authentication Flow
```
User → Clerk Login → JWT Token → FastAPI validates → Account lookup
CLI → API Key (~/.rgrid/credentials) → FastAPI validates → Account lookup
```

### Network Isolation
- **Private Network:** All worker-to-control communication via 10.0.0.0/16
- **Public Internet:** Only API endpoint exposed (HTTPS)
- **Container Network:** Disabled by default (use `network=true` flag to enable)

### Container Sandboxing
- **Read-Only Root FS:** Containers can't modify system files
- **No Privileged Mode:** Can't escape container
- **Resource Limits:** CPU/memory cgroups enforced
- **No Network:** Containers isolated unless explicitly enabled

### Secrets Management
- **API Keys:** Hashed with bcrypt before storage
- **Environment Variables:** Encrypted in database, decrypted at runtime
- **Clerk Webhook Secret:** Validated on all user sync events

---

## 📊 Future Evolution Paths

### 1. Estimated Micros Added (EMA)
**Problem:** Workers provisioned based on queue depth, but some jobs are 10s while others are 10min
**Solution:** Track job duration patterns, provision based on estimated total compute time

**Schema Addition:**
```python
class Execution:
    estimated_duration_seconds: int  # User hint or ML prediction
    actual_duration_seconds: int     # Measured after completion
```

**Algorithm:**
```python
total_estimated_micros = sum(job.estimated_duration_seconds for job in queue)
required_worker_hours = total_estimated_micros / 3600
provision_workers = ceil(required_worker_hours)
```

### 2. Compute Pricing Amortization Logic (CPAL)
**Problem:** Simple "cost / jobs in hour" doesn't account for job duration variance
**Solution:** Proportional cost distribution based on actual runtime

**Algorithm:**
```python
# Current (simple)
cost_per_job = hourly_cost / job_count

# Future (proportional)
total_seconds = sum(job.duration for job in jobs_in_hour)
job.finalized_cost = hourly_cost * (job.duration / total_seconds)
```

### 3. Runtime Plugins
**Problem:** Only Python supported, users want Node.js, Go, Rust, etc.
**Solution:** Plugin architecture for language runtimes

**Schema Addition:**
```python
class Execution:
    runtime: str  # 'python', 'node', 'go', 'rust'
    runtime_version: str  # '3.11', '20', '1.21', 'stable'
```

**Docker Images:**
```
rgrid-python:3.11
rgrid-node:20
rgrid-go:1.21
rgrid-rust:stable
```

### 4. Multi-Cloud Support
**Problem:** Vendor lock-in to Hetzner
**Solution:** Provider abstraction layer

**Schema Addition:**
```python
class Worker:
    provider: str  # 'hetzner', 'aws', 'gcp'

class ServerType:
    provider: str
    instance_type: str  # 'cx22', 't3.small', 'e2-small'
```

**Service Layer:**
```python
class ProviderService(ABC):
    @abstractmethod
    def provision_worker(server_type: ServerType) -> Worker:
        pass

class HetznerProvider(ProviderService):
    def provision_worker(self, server_type):
        # Hetzner API calls
        ...
```

---

## 🎯 Implementation Readiness

### ✅ Ready to Start Implementation

All architecture decisions finalized and documented:
- [x] Project structure defined
- [x] Database schema complete (21 tables)
- [x] Ray cluster architecture finalized
- [x] Docker image management strategy set
- [x] File upload/download flow designed
- [x] Authentication pattern chosen
- [x] API route structure (LLM-friendly)
- [x] WebSocket implementation designed
- [x] Worker provisioning logic defined
- [x] Content-hash caching strategy set
- [x] Error handling patterns established
- [x] Logging format standardized

### 📋 Next Steps (BMad Method)

1. **Review Architecture** - User reviews `architecture.md` for any adjustments
2. **Solutioning Gate Check** - Validate PRD ↔ Architecture alignment
3. **Create Epics & Stories** - Break down PRD into implementable units
4. **Sprint Planning** - Generate sprint status tracking
5. **Implementation** - Begin Phase 4 development

### 📚 Key Documents

- **Full Architecture:** [architecture.md](./architecture.md) (75+ pages)
- **PRD:** [PRD.md](./PRD.md) (product requirements)
- **Project Brief:** [PROJECT_BRIEF.md](./PROJECT_BRIEF.md) (vision)
- **Workflow Status:** [bmm-workflow-status.yaml](./bmm-workflow-status.yaml)

---

## 💡 Key Takeaways

### What Makes This Architecture Special?

1. **MICRONS Everywhere** - No float imprecision, exact integer math for tiny costs
2. **Shared Worker Pool** - Not siloed by account, maximizes utilization
3. **Billing Hour Optimization** - Keep workers until hour ends, amortize costs
4. **LLM-Agent Friendly** - Every decision optimizes for AI readability/modification
5. **Future-Proof** - Clear evolution paths (EMA, CPAL, runtime plugins)
6. **Multi-Tenant from Day 1** - Jumpstart pattern, ready for scale
7. **Hetzner All-In-One** - €10.49/month base, sub-€1/hour for workers
8. **Content-Hash Caching** - 3-level caching for instant results
9. **Convention Over Configuration** - Scripts run remotely identical to local
10. **Ray Distributed Computing** - Scales from 1 worker to 100+ seamlessly

### Design Philosophy

> **"Dropbox Simplicity"**
> Scripts should run remotely with zero code changes. Users shouldn't think about infrastructure.

### Success Metrics

- **Developer Experience:** `rgrid run script.py` feels identical to `python script.py`
- **Cost Efficiency:** Workers utilized >80% during billing hour
- **Reliability:** Jobs complete or fail deterministically (no "lost jobs")
- **Multi-Tenancy:** Account isolation perfect, worker sharing seamless

---

**Architecture Status:** ✅ **COMPLETE**
**Ready for Implementation:** ✅ **YES**
**Next Workflow:** Solutioning Gate Check or Epic Breakdown

---

*Generated by Claude Code via BMad Method Architecture Workflow*
*Date: 2025-11-15*
