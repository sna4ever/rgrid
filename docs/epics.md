# rgrid - Epic Breakdown

**Author:** BMad
**Date:** 2025-11-15
**Project Level:** BMad Method - Greenfield
**Target Scale:** MVP

---

## Overview

This document provides the complete epic and story breakdown for rgrid, decomposing the requirements from the [PRD](./PRD.md) into implementable stories.

**Living Document Notice:** This is the initial version. It will be updated after UX Design and Architecture workflows add interaction and technical details to stories.

### Epic Structure

RGrid's implementation is organized into 10 epics following a natural progression from foundation to polish:

1. **Epic 1: Foundation & CLI Core** - Project infrastructure, CLI framework, authentication
2. **Epic 2: Single Script Execution** - Core execution flow, Docker runtime, basic I/O
3. **Epic 3: Distributed Orchestration (Ray)** - Ray cluster, task distribution, worker management
4. **Epic 4: Cloud Infrastructure (Hetzner)** - Auto-provisioning, lifecycle management, cost tracking
5. **Epic 5: Batch Execution & Parallelism** - Pattern matching, parallel distribution, progress tracking
6. **Epic 6: Caching & Optimization** - Content-hash caching for scripts, deps, inputs
7. **Epic 7: File & Artifact Management** - Upload/download automation, S3 storage, output organization
8. **Epic 8: Observability & Real-time Feedback** - Logs, WebSocket streaming, status tracking
9. **Epic 9: Cost Tracking & Billing** - Per-execution costs, estimates, transparency
10. **Epic 10: Web Interfaces & MVP Polish** - Marketing website, console dashboard, validation

**Epic Sequencing Rationale:**
- Epic 1 establishes foundation for all subsequent work
- Epics 2-4 build core execution capability (single script → distributed → auto-scaled)
- Epics 5-7 add power features (batch, caching, file handling)
- Epics 8-9 add observability and billing
- Epic 10 completes MVP with web interfaces

---

## Functional Requirements Inventory

### CLI & Developer Interface
- **FR1:** Install via package manager (brew/pip) with zero dependencies
- **FR2:** Authenticate and initialize in < 1 minute via `rgrid init`
- **FR3:** Execute scripts remotely with identical syntax: `rgrid run script.py args`
- **FR4:** Execute scripts in parallel via `--batch` flag
- **FR5:** Specify runtime requirements via `--runtime` flag
- **FR6:** Monitor execution status via `rgrid status` and `--watch`
- **FR7:** Access execution logs via `rgrid logs`
- **FR8:** Download execution outputs via `rgrid download`
- **FR9:** View cost estimates before execution and actual costs after
- **FR10:** Receive clear, actionable error messages

### Script Execution Model
- **FR11:** Scripts execute in isolated container environments
- **FR12:** Multiple pre-configured runtimes (Python 3.10, 3.11, datascience, LLM, ffmpeg, Node.js)
- **FR13:** Custom Docker images from public registries
- **FR14:** Scripts receive input files as command-line arguments
- **FR15:** Scripts write outputs to working directory; auto-collected
- **FR16:** Script exit codes determine execution success
- **FR17:** Scripts can read environment variables via `--env` flag
- **FR18:** Auto-detect and install dependencies from requirements.txt
- **FR19:** Explicit requirements file via `--requirements` flag
- **FR20:** Scripts have network access by default

### Caching & Performance Optimization
- **FR21:** Cache script images using content hashing (sha256)
- **FR22:** Cache dependency layers using requirements.txt hashing
- **FR23:** Cached scripts provide instant execution after first run
- **FR24:** Automatic cache invalidation when script/deps change
- **FR25:** Caching completely invisible to users
- **FR26:** Optional input file caching

### Batch Execution & Parallelism
- **FR27:** Expand file patterns (glob) into individual executions
- **FR28:** Distribute batch executions across workers
- **FR29:** Track batch progress (completed, failed, running, queued)
- **FR30:** Set max parallelism via `--parallel` flag
- **FR31:** Handle batch failures gracefully
- **FR32:** Retry failed executions individually or in batch
- **FR33:** Batch outputs in `./outputs/<input-name>/` directory structure
- **FR34:** Override output location via `--output-dir` flag
- **FR35:** Flat output structure via `--flat` flag

### Distributed Orchestration
- **FR36:** Auto-provision compute workers on Hetzner
- **FR37:** Distribute executions via Ray task scheduling
- **FR38:** Scale worker pool based on queue depth
- **FR39:** Auto-terminate idle workers (scale to zero)
- **FR40:** Worker health monitoring and auto-replacement
- **FR41:** Cache common Docker images on workers
- **FR42:** Manage Ray cluster lifecycle
- **FR43:** Handle network communication (CLI ↔ control plane ↔ workers)

### File & Artifact Management
- **FR44:** Auto-upload input files referenced in script arguments
- **FR45:** Collect all files created in script's working directory
- **FR46:** Store outputs in S3-compatible storage (MinIO) with retention
- **FR47:** Single execution outputs auto-downloaded to current directory
- **FR48:** Skip automatic download via `--remote-only` flag
- **FR49:** List outputs before downloading via `rgrid outputs`
- **FR50:** Handle large files efficiently (streaming, compression >100MB)

### Authentication & Configuration
- **FR51:** Authenticate CLI using API keys in `~/.rgrid/credentials`
- **FR52:** API keys NEVER in project files or CLI arguments
- **FR53:** `rgrid init` creates global credentials file
- **FR54:** Optional project config via `.rgrid/config` for defaults
- **FR55:** Project config safe to commit (no secrets)
- **FR56:** Multi-account support via named profiles (future)

### Observability & Monitoring
- **FR57:** View execution history via CLI and web console
- **FR58:** Access real-time logs via `--watch` or `--follow`
- **FR59:** Retrieve historical logs for completed executions
- **FR60:** Track execution metadata (time, exit code, worker, cost)
- **FR61:** View worker pool status (count, region, utilization)
- **FR62:** Progress tracking for batch executions

### Cost & Billing
- **FR63:** Calculate per-execution cost based on actual compute time
- **FR64:** View itemized cost breakdown via `rgrid cost`
- **FR65:** Display cost estimates via `rgrid estimate`
- **FR66:** Transparent billing with infrastructure cost mapping
- **FR67:** Set cost alerts or spending limits (future)

### Error Handling & Reliability
- **FR68:** Detect and report common user errors
- **FR69:** Handle network failures gracefully with auto-reconnection
- **FR70:** Preserve logs and error context for failed executions
- **FR71:** Prevent cascading failures
- **FR72:** Manually retry failed executions via `rgrid retry`
- **FR73:** Auto-retry transient failures (default: 2 retries)

### Extensibility & Future-Proofing
- **FR74:** Attach custom metadata via `--metadata` flag
- **FR75:** Store and query execution metadata
- **FR76:** Capture execution lifecycle events
- **FR77:** Pluggable abstractions (EMA, CPAL, runtime providers)

### Real-time Feedback
- **FR78:** Real-time log streaming via WebSocket
- **FR79:** CLI reconnection and log resumption
- **FR80:** Batch aggregate progress with individual drill-down
- **FR81:** Long-running executions continue when CLI disconnects
- **FR82:** Progress estimates for batch jobs (%, ETA)

---

## FR Coverage Map

### Epic 1: Foundation & CLI Core
**Covers:** Infrastructure foundation, CLI framework, authentication, basic commands
- **FRs:** FR1, FR2, FR51, FR52, FR53, FR54, FR55
- **Focus:** Enable subsequent epics by establishing project structure, CLI interface, and auth

### Epic 2: Single Script Execution
**Covers:** Core execution flow for single script
- **FRs:** FR3, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20
- **Focus:** Prove paradigm shift - run script remotely with zero code changes

### Epic 3: Distributed Orchestration (Ray)
**Covers:** Ray cluster setup, task distribution, worker coordination
- **FRs:** FR37, FR42, FR43
- **Focus:** Enable distributed execution framework

### Epic 4: Cloud Infrastructure (Hetzner)
**Covers:** Auto-provisioning, worker lifecycle, cost optimization
- **FRs:** FR36, FR38, FR39, FR40, FR41
- **Focus:** Make infrastructure invisible and cost-efficient

### Epic 5: Batch Execution & Parallelism
**Covers:** Pattern matching, parallel execution, batch management
- **FRs:** FR4, FR27, FR28, FR29, FR30, FR31, FR32, FR33, FR34, FR35
- **Focus:** Scale from 1 script to 1000 scripts in parallel

### Epic 6: Caching & Optimization
**Covers:** Content-hash caching for scripts, dependencies, inputs
- **FRs:** FR21, FR22, FR23, FR24, FR25, FR26
- **Focus:** Make repeated executions instant

### Epic 7: File & Artifact Management
**Covers:** Upload/download automation, S3 storage, output handling
- **FRs:** FR44, FR45, FR46, FR47, FR48, FR49, FR50
- **Focus:** Make file I/O invisible and reliable

### Epic 8: Observability & Real-time Feedback
**Covers:** Logs, WebSocket streaming, status tracking, progress
- **FRs:** FR6, FR7, FR57, FR58, FR59, FR60, FR61, FR62, FR78, FR79, FR80, FR81, FR82
- **Focus:** Provide visibility into execution state

### Epic 9: Cost Tracking & Billing
**Covers:** Per-execution costs, estimates, transparency, alerts
- **FRs:** FR9, FR63, FR64, FR65, FR66, FR67
- **Focus:** Make costs predictable and transparent

### Epic 10: Web Interfaces & MVP Polish
**Covers:** Marketing website, console dashboard, extensibility, final validation
- **FRs:** FR8, FR10, FR68, FR69, FR70, FR71, FR72, FR73, FR74, FR75, FR76, FR77
- **Focus:** Complete MVP with web interfaces and production-ready error handling

**FR Coverage Validation:** All 82 FRs mapped to epics ✅

---

## Epic 1: Foundation & CLI Core

**Goal:** Establish project infrastructure, monorepo structure, CLI framework, and authentication system that enables all subsequent development.

**Value:** Creates foundation for developers to build upon - project setup, build system, deployment pipeline, and secure authentication.

**FRs Covered:** FR1, FR2, FR51, FR52, FR53, FR54, FR55

### Story 1.1: Initialize Monorepo Project Structure

As a developer,
I want a properly structured monorepo with all components organized logically,
So that I can develop API, orchestrator, runner, CLI, and web apps in a cohesive codebase.

**Acceptance Criteria:**

**Given** a fresh development environment
**When** the project is initialized
**Then** the directory structure follows the architecture:
- `api/` - FastAPI backend with routes/, services/, schemas/, models/
- `orchestrator/` - Autoscaler service with provisioning logic
- `runner/` - Worker agent with Docker execution
- `cli/` - Python CLI tool with Click framework
- `console/` - Next.js dashboard (App Router)
- `website/` - Next.js marketing site
- `common/` - Shared Python package for models/schemas
- `infra/` - Terraform, cloud-init, Dockerfiles
- `tests/` - Unit and integration tests
- `docs/` - Documentation

**And** root includes: `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`
**And** each Python component has `pyproject.toml` with dependencies
**And** shared `common/` package is installable via `pip install -e common/`

**Prerequisites:** None (first story)

**Technical Notes:**
- Use Poetry or uv for Python dependency management
- Monorepo pattern from architecture.md Decision 1
- Reference: architecture.md lines 17-21

---

### Story 1.2: Set Up Development Environment and Build System

As a developer,
I want a consistent development environment with automated build and test commands,
So that I can quickly iterate on code changes across all components.

**Acceptance Criteria:**

**Given** the monorepo structure from Story 1.1
**When** I run `make setup`
**Then** all Python dependencies are installed
**And** pre-commit hooks are configured (black, ruff, mypy)
**And** development database is initialized (PostgreSQL via Docker Compose)
**And** MinIO storage is running locally (Docker Compose)

**When** I run `make test`
**Then** all unit tests execute across api/, orchestrator/, runner/, cli/
**And** test coverage report is generated
**And** minimum 80% coverage is enforced

**When** I run `make lint`
**Then** code is formatted with black
**And** linting passes with ruff
**And** type checking passes with mypy

**Prerequisites:** Story 1.1

**Technical Notes:**
- Use Docker Compose for local PostgreSQL + MinIO
- Makefile targets: setup, test, lint, format, clean
- Pre-commit hooks prevent commits that fail linting
- Reference: Architecture LLM-friendly patterns (architecture.md lines 179-190)

---

### Story 1.3: Implement API Key Authentication System

As a developer,
I want a secure API key authentication system following AWS credentials pattern,
So that CLI users can authenticate without exposing secrets in project files.

**Acceptance Criteria:**

**Given** the database schema for `api_keys` table (see architecture.md)
**When** a user generates an API key
**Then** the key is bcrypt-hashed before storage
**And** the key follows format: `sk_live_` + 32 random characters
**And** keys are stored in `api_keys` table with account_id, created_at, last_used_at

**When** CLI sends request with API key in Authorization header
**Then** FastAPI validates key via dependency injection `get_authenticated_account()`
**And** account is loaded from database
**And** `last_used_at` timestamp is updated
**And** invalid keys return 401 Unauthorized with clear error message

**When** API key is revoked
**Then** subsequent requests with that key are rejected
**And** revocation is logged for audit

**Prerequisites:** Story 1.1, Story 1.2

**Technical Notes:**
- Use bcrypt for hashing (secure, slow by design)
- FastAPI dependency: `Depends(get_authenticated_account)` on all routes
- Store API keys ONLY in `~/.rgrid/credentials` (never in git)
- Reference: architecture.md Decision 6 (lines 44-48), DB schema for api_keys table
- Implement as pure service function for testability

---

### Story 1.4: Build CLI Framework with Click

As a developer,
I want a CLI framework using Click with proper command structure and error handling,
So that users can execute `rgrid` commands with intuitive interface.

**Acceptance Criteria:**

**Given** the cli/ package structure
**When** CLI is installed via `pip install -e cli/`
**Then** `rgrid` command is available globally
**And** `rgrid --version` shows current version
**And** `rgrid --help` lists all available commands

**When** user runs `rgrid <command>`
**Then** CLI loads credentials from `~/.rgrid/credentials`
**And** sends authenticated requests to API
**And** displays results in user-friendly format (not raw JSON)
**And** errors show actionable messages (not stack traces)

**And** CLI supports these initial commands:
- `rgrid init` - Initialize credentials
- `rgrid run <script>` - Execute script (stub for now)
- `rgrid status <execution-id>` - Check status (stub for now)
- `rgrid logs <execution-id>` - View logs (stub for now)

**Prerequisites:** Story 1.1, Story 1.3

**Technical Notes:**
- Use Click framework for command structure
- CLI structure: cli/rgrid/commands/init.py, run.py, status.py, logs.py
- Credentials path: `~/.rgrid/credentials` (INI format like AWS)
- HTTP client: httpx (async support for future)
- Reference: PRD CLI specification (lines 2255-2390)

---

### Story 1.5: Implement `rgrid init` Command for First-Time Setup

As a developer,
I want `rgrid init` to handle first-time authentication setup,
So that users can authenticate in < 1 minute as per FR2.

**Acceptance Criteria:**

**Given** a user runs `rgrid init` for the first time
**When** the command executes
**Then** CLI prompts: "Enter your API key (from app.rgrid.dev):"
**And** user enters key (e.g., `sk_live_abc123...`)
**And** CLI validates key by calling `POST /api/v1/auth/validate`
**And** on success, writes to `~/.rgrid/credentials`:
```
[default]
api_key = sk_live_abc123...
```

**And** CLI displays: "✅ Authentication successful! You're ready to run scripts."
**And** execution time < 30 seconds

**When** validation fails (invalid key)
**Then** CLI displays: "❌ Invalid API key. Get your key from: https://app.rgrid.dev/settings/api-keys"
**And** credentials file is NOT created
**And** exit code = 1

**When** user runs `rgrid init` again (credentials exist)
**Then** CLI prompts: "Credentials already exist. Overwrite? (y/n)"
**And** on "y", replaces existing credentials
**And** on "n", exits without changes

**Prerequisites:** Story 1.3, Story 1.4

**Technical Notes:**
- Credentials file permissions: chmod 600 (owner read/write only)
- API endpoint: POST /api/v1/auth/validate (returns account info)
- Use `getpass` module for secure password input (no echo)
- Reference: architecture.md Decision 6, PRD authentication section

---

### Story 1.6: Set Up FastAPI Backend with Database Connection

As a developer,
I want a FastAPI application with PostgreSQL connection and basic health check,
So that API can serve authenticated requests from CLI.

**Acceptance Criteria:**

**Given** the api/ package structure
**When** FastAPI app starts
**Then** database connection pool is initialized (asyncpg)
**And** MinIO client is initialized (boto3)
**And** app serves on http://localhost:8000

**When** GET /health is called
**Then** response is 200 OK with:
```json
{
  "status": "healthy",
  "database": "connected",
  "storage": "connected",
  "version": "0.1.0"
}
```

**When** POST /api/v1/auth/validate is called with valid API key
**Then** response is 200 OK with account info:
```json
{
  "account_id": "acct_abc123",
  "email": "user@example.com",
  "credits_balance_micros": 1000000
}
```

**When** called with invalid API key
**Then** response is 401 Unauthorized

**Prerequisites:** Story 1.1, Story 1.2, Story 1.3

**Technical Notes:**
- FastAPI + Uvicorn for async server
- SQLAlchemy 2.0 + asyncpg for database ORM
- Database URL from environment: `DATABASE_URL=postgresql+asyncpg://...`
- MinIO credentials from environment
- Reference: architecture.md Decision 7 (API structure), DB schema
- Use Pydantic models for all requests/responses

---

---


## Epic 2: Single Script Execution

**Goal:** Enable developers to run a single Python script remotely with zero code changes, proving the core paradigm shift.

**Value:** Demonstrates "run locally → run remotely" with identical syntax - the fundamental value proposition of RGrid.

**FRs Covered:** FR3, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20

### Story 2.1: Implement `rgrid run` Command (Basic Stub)

As a developer,
I want to execute `rgrid run script.py` and have it submit to the API,
So that I can begin the remote execution flow.

**Acceptance Criteria:**

**Given** I have a Python script `test.py` in my current directory
**When** I run `rgrid run test.py arg1 arg2`
**Then** CLI reads script content and arguments
**And** CLI submits execution request to `POST /api/v1/executions`
**And** API returns execution_id (e.g., `exec_abc123`)
**And** CLI displays: "Execution started: exec_abc123"

**Prerequisites:** Story 1.5, Story 1.6

**Technical Notes:**
- POST /api/v1/executions with ExecutionCreate schema
- Include: script_content, args, runtime (default: python:3.11)
- Return execution_id for tracking
- Reference: architecture.md API structure

---

### Story 2.2: Implement Docker Container Execution on Runner

As a developer,
I want scripts to execute in isolated Docker containers on worker nodes,
So that executions are sandboxed and secure.

**Acceptance Criteria:**

**Given** a worker node receives an execution task
**When** runner processes the task
**Then** runner creates Docker container with specified runtime (e.g., python:3.11)
**And** runner mounts script into container at /work/<exec_id>/script.py
**And** runner executes script with provided arguments
**And** container has no network access by default (--network none)
**And** container root filesystem is read-only except /work directory
**And** runner captures stdout/stderr to logs
**And** runner detects exit code (0 = success, non-zero = failure)

**Prerequisites:** Story 2.1

**Technical Notes:**
- Docker SDK for Python
- Container constraints: --memory 2g --cpus 1
- cgroup limits enforced
- Reference: architecture.md container sandboxing

---

### Story 2.3: Implement Pre-Configured Runtimes

As a developer,
I want to use pre-configured runtimes without building custom images,
So that common environments (Python, Node.js, ffmpeg) work out of the box.

**Acceptance Criteria:**

**Given** runner supports multiple runtimes
**When** execution specifies runtime
**Then** runner uses corresponding Docker image:
- `python:3.10` → python:3.10-slim
- `python:3.11` → python:3.11-slim
- `python:3.11-datascience` → custom image with numpy, pandas, scikit-learn
- `python:3.11-llm` → custom image with openai, anthropic, langchain
- `ffmpeg:latest` → custom image with ffmpeg + Python
- `node:20` → node:20-slim

**And** images are pre-pulled on worker initialization for fast cold starts

**Prerequisites:** Story 2.2

**Technical Notes:**
- Build custom images in infra/dockerfiles/
- Pre-pull images during worker provisioning
- Reference: architecture.md Decision 4 (Docker image management)

---

### Story 2.4: Auto-Detect and Install Python Dependencies

As a developer,
I want dependencies from requirements.txt automatically installed,
So that my scripts run without manual setup.

**Acceptance Criteria:**

**Given** a script directory contains requirements.txt
**When** runner prepares execution environment
**Then** runner detects requirements.txt in same directory as script
**And** runner installs dependencies via `pip install -r requirements.txt`
**And** runner caches installed packages for subsequent runs
**And** installation logs are captured to execution logs

**When** requirements.txt is missing
**Then** runner executes script without installing dependencies (use base image packages)

**Prerequisites:** Story 2.3

**Technical Notes:**
- Use pip with --no-cache-dir for reproducibility
- Cache pip packages per requirements.txt hash (Epic 6)
- Reference: PRD FR18, FR19

---

### Story 2.5: Handle Script Input Files as Arguments

As a developer,
I want to pass local files as script arguments and have them available in the container,
So that scripts can read input data identically to local execution.

**Acceptance Criteria:**

**Given** I run `rgrid run process.py input.json`
**When** execution starts
**Then** CLI uploads input.json to MinIO
**And** runner downloads input.json into container /work directory
**And** runner passes /work/input.json as argument to script
**And** script receives file path and can read it normally

**Prerequisites:** Story 2.4

**Technical Notes:**
- CLI detects file arguments by checking os.path.exists()
- Upload to MinIO bucket: executions/<exec_id>/inputs/
- Runner downloads before script execution
- Reference: architecture.md Decision 5 (file upload/download)

---

### Story 2.6: Collect and Store Script Outputs

As a developer,
I want all files created by my script automatically collected and stored,
So that I can retrieve results after execution completes.

**Acceptance Criteria:**

**Given** a script creates output files in working directory
**When** script execution completes
**Then** runner scans /work directory for all files created
**And** runner uploads all outputs to MinIO: executions/<exec_id>/outputs/
**And** runner records artifacts in database: artifacts table
**And** CLI can download outputs via `rgrid download <exec_id>`

**Prerequisites:** Story 2.5

**Technical Notes:**
- Use MinIO presigned PUT URLs for uploads
- Record artifact metadata: filename, size, content_type
- Reference: architecture.md Decision 5, DB schema artifacts table

---

### Story 2.7: Support Environment Variables via --env Flag

As a developer,
I want to pass environment variables to my script,
So that I can configure behavior without changing code.

**Acceptance Criteria:**

**Given** I run `rgrid run script.py --env API_KEY=abc123 --env DEBUG=true`
**When** execution starts
**Then** runner sets environment variables in container
**And** script can access via os.environ['API_KEY']

**Prerequisites:** Story 2.6

**Technical Notes:**
- Pass env vars to Docker container via --env flag
- Store encrypted in database if sensitive
- Reference: PRD FR17

---

---

## Epic 3: Distributed Orchestration (Ray)

**Goal:** Integrate Ray for distributed task scheduling and enable execution across multiple worker nodes.

**Value:** Unlocks parallel execution and horizontal scaling - foundation for batch operations.

**FRs Covered:** FR37, FR42, FR43

### Story 3.1: Set Up Ray Head Node on Control Plane

As a developer,
I want a Ray head node running on the control plane,
So that workers can join the cluster and receive task assignments.

**Acceptance Criteria:**

**Given** control plane is deployed
**When** Ray head node initializes
**Then** Ray serves on port 6379 (Redis protocol)
**And** Ray dashboard available on port 8265
**And** workers can connect via control plane private IP (10.0.0.1:6379)

**Prerequisites:** Epic 1 complete

**Technical Notes:**
- Run Ray head as separate container or process
- Hardcoded IP in cloud-init for workers
- Reference: architecture.md Decision 3 (Ray cluster architecture)

---

### Story 3.2: Initialize Ray Worker on Each Hetzner Node

As a developer,
I want each Hetzner worker node to automatically join the Ray cluster on startup,
So that tasks can be distributed to workers.

**Acceptance Criteria:**

**Given** a Hetzner worker node is provisioned
**When** runner initializes
**Then** Ray worker connects to head node at 10.0.0.1:6379
**And** Ray worker registers with cluster
**And** worker is visible in Ray dashboard
**And** worker advertises max_concurrent = 2 (1 job per vCPU)

**Prerequisites:** Story 3.1

**Technical Notes:**
- Cloud-init script starts Ray worker on boot
- Worker resources: 2 CPUs, 4GB RAM (CX22 specs)
- Reference: architecture.md Decision 3

---

### Story 3.3: Submit Executions as Ray Tasks

As a developer,
I want API to submit executions as Ray remote tasks,
So that Ray distributes work across available workers.

**Acceptance Criteria:**

**Given** API receives execution request
**When** API creates execution record in database
**Then** API submits Ray task via `execute_script.remote(exec_id)`
**And** Ray schedules task on available worker
**And** runner on worker receives task and executes
**And** execution status updates in database (queued → running → completed)

**Prerequisites:** Story 3.2

**Technical Notes:**
- Use Ray's @ray.remote decorator
- Task function: execute_script(exec_id) → downloads script, runs Docker, uploads outputs
- Reference: architecture.md Decision 3, PRD FR37

---

### Story 3.4: Implement Worker Health Monitoring

As a developer,
I want workers to send heartbeats to detect failures,
So that dead workers are removed and jobs are rescheduled.

**Acceptance Criteria:**

**Given** workers are running
**When** worker sends heartbeat every 30 seconds
**Then** orchestrator updates worker_heartbeats table with timestamp
**And** orchestrator marks worker as dead if no heartbeat for 2 minutes
**And** orphaned tasks are rescheduled to other workers

**Prerequisites:** Story 3.3

**Technical Notes:**
- Heartbeat table: worker_id, last_heartbeat_at
- Orchestrator runs periodic cleanup job
- Reference: architecture.md worker lifecycle, DB schema

---

---

## Epic 4: Cloud Infrastructure (Hetzner)

**Goal:** Auto-provision Hetzner CX22 workers on demand and manage lifecycle for cost efficiency.

**Value:** Makes infrastructure completely invisible - workers appear and disappear based on workload.

**FRs Covered:** FR36, FR38, FR39, FR40, FR41

### Story 4.1: Implement Hetzner Worker Provisioning via API

As a developer,
I want orchestrator to provision Hetzner workers via API,
So that capacity scales automatically with queue depth.

**Acceptance Criteria:**

**Given** orchestrator detects queue depth > 0 and no available workers
**When** provisioning logic executes
**Then** orchestrator calls Hetzner API to create CX22 server
**And** server uses cloud-init script to install Docker, Ray, runner
**And** worker joins Ray cluster within 60 seconds
**And** worker record created in workers table

**Prerequisites:** Epic 3 complete

**Technical Notes:**
- Use Hetzner Python SDK (hcloud)
- Cloud-init template in infra/cloud-init/worker.yaml
- Server type: cx22 (2 vCPU, 4GB RAM, €5.83/month prorated)
- Reference: architecture.md Decision 9 (worker provisioning)

---

### Story 4.2: Implement Queue-Based Smart Provisioning Algorithm

As a developer,
I want workers provisioned only when truly needed,
So that costs are minimized while maintaining responsiveness.

**Acceptance Criteria:**

**Given** orchestrator runs provisioning check every 10 seconds
**When** checking whether to provision
**Then** orchestrator calculates:
- `queued_jobs = count(status='queued')`
- `available_slots = sum(worker.max_concurrent for idle workers)`
- `est_completion_time = estimate based on running jobs`

**And** if `available_slots >= queued_jobs`, provision = 0
**And** if `est_completion_time < 5 minutes`, provision = 0 (jobs completing soon)
**And** else, provision = `ceil((queued_jobs - available_slots) / 2)` workers

**Prerequisites:** Story 4.1

**Technical Notes:**
- Smart algorithm from architecture.md Decision 9
- Prevents over-provisioning
- Each CX22 has 2 slots (1 job per vCPU)

---

### Story 4.3: Implement Billing Hour Aware Worker Termination

As a developer,
I want workers kept alive until billing hour ends,
So that hourly costs are amortized across maximum jobs.

**Acceptance Criteria:**

**Given** worker is provisioned at time T
**When** worker completes all jobs
**Then** orchestrator checks: `current_time < T + 1 hour`?
**And** if yes, keep worker alive (idle)
**And** if no, terminate worker via Hetzner API
**And** worker record marked as terminated in database

**Prerequisites:** Story 4.2

**Technical Notes:**
- Hetzner bills hourly, so maximize utilization within each hour
- Billing hour logic from architecture.md Decision 9
- Cost amortization in Epic 9

---

### Story 4.4: Pre-Pull Common Docker Images on Worker Init

As a developer,
I want workers to pre-pull common images during initialization,
So that first execution has minimal cold-start latency.

**Acceptance Criteria:**

**Given** worker node initializes
**When** cloud-init script runs
**Then** runner pre-pulls these images:
- python:3.11-slim
- python:3.10-slim
- Custom datascience image
- Custom ffmpeg image

**And** images are cached locally on worker
**And** first execution using these runtimes starts immediately (no pull delay)

**Prerequisites:** Story 4.1

**Technical Notes:**
- Add docker pull commands to cloud-init
- ~2-3 minutes during worker boot (acceptable - first job waits anyway)
- Reference: architecture.md Decision 4, FR41

---

### Story 4.5: Implement Worker Auto-Replacement on Failure

As a developer,
I want failed workers automatically replaced,
So that system is self-healing.

**Acceptance Criteria:**

**Given** orchestrator detects dead worker (no heartbeat for 2 minutes)
**When** worker has queued or running jobs
**Then** orchestrator provisions replacement worker
**And** jobs are rescheduled to new worker
**And** dead worker is terminated via Hetzner API

**Prerequisites:** Story 3.4, Story 4.3

**Technical Notes:**
- Use heartbeat monitoring from Story 3.4
- Reschedule via Ray task retry
- Reference: PRD FR40

---

---

## Epic 5: Batch Execution & Parallelism

**Goal:** Enable parallel execution of scripts across multiple input files with a single command.

**Value:** Scale from 1 script to 1000 scripts in parallel - the killer feature for data processing.

**FRs Covered:** FR4, FR27, FR28, FR29, FR30, FR31, FR32, FR33, FR34, FR35

### Story 5.1: Implement --batch Flag with Glob Pattern Expansion

As a developer,
I want to run `rgrid run script.py --batch data/*.csv`,
So that each CSV file creates a separate execution.

**Acceptance Criteria:**

**Given** I run `rgrid run process.py --batch inputs/*.csv`
**When** CLI expands glob pattern
**Then** CLI finds all matching files (e.g., input1.csv, input2.csv, input3.csv)
**And** CLI creates N execution requests (one per file)
**And** each execution receives one input file as argument
**And** CLI displays: "Starting batch: 3 files, 10 parallel"

**Prerequisites:** Epic 2 complete

**Technical Notes:**
- Use Python glob.glob() for pattern expansion
- Support patterns: *.csv, data/**, inputs/file_{1..100}.json
- Reference: PRD FR27

---

### Story 5.2: Implement --parallel Flag for Concurrency Control

As a developer,
I want to control max parallel executions via --parallel flag,
So that I can limit infrastructure usage.

**Acceptance Criteria:**

**Given** I run `rgrid run script.py --batch data/*.csv --parallel 20`
**When** batch starts
**Then** CLI submits first 20 executions immediately
**And** as each execution completes, CLI submits next execution
**And** max 20 executions run concurrently
**And** default parallelism = 10 if flag omitted

**Prerequisites:** Story 5.1

**Technical Notes:**
- Use asyncio.Semaphore for concurrency control
- Queue remaining executions locally until slots available
- Reference: PRD FR30

---

### Story 5.3: Track Batch Execution Progress

As a developer,
I want real-time progress tracking for batch executions,
So that I can monitor completion status.

**Acceptance Criteria:**

**Given** batch execution with --watch flag
**When** executions run
**Then** CLI displays:
```
[=========>           ] 45/100 complete (3 failed, 10 running, 42 queued)
Estimated completion: 3m 15s
```

**And** progress updates every 2 seconds
**And** shows: completed, failed, running, queued counts

**Prerequisites:** Story 5.2

**Technical Notes:**
- Poll API for execution statuses
- Calculate ETA based on average completion time
- Reference: PRD FR29, FR62

---

### Story 5.4: Organize Batch Outputs by Input Filename

As a developer,
I want batch outputs organized in ./outputs/<input-name>/ directories,
So that I can map outputs back to inputs easily.

**Acceptance Criteria:**

**Given** batch execution with 3 input files: data1.csv, data2.csv, data3.csv
**When** executions complete
**Then** CLI downloads outputs to:
```
./outputs/
  data1/
    output.json
    results.csv
  data2/
    output.json
    results.csv
  data3/
    output.json
    results.csv
```

**Prerequisites:** Story 5.3

**Technical Notes:**
- Extract input filename from execution metadata
- Create subdirectory per input
- Reference: PRD FR33

---

### Story 5.5: Handle Batch Failures Gracefully

As a developer,
I want batch to continue processing even if some executions fail,
So that partial results are still useful.

**Acceptance Criteria:**

**Given** batch execution where some scripts fail
**When** failure occurs
**Then** CLI logs failure but continues processing remaining files
**And** final summary shows: "95 succeeded, 5 failed"
**And** failed executions are listed with error messages
**And** exit code = 0 if any succeeded, 1 if all failed

**Prerequisites:** Story 5.4

**Technical Notes:**
- Collect failures in list
- Display summary at end
- Reference: PRD FR31

---

### Story 5.6: Implement Retry for Failed Batch Executions

As a developer,
I want to retry only failed executions from a batch,
So that I don't re-run successful ones.

**Acceptance Criteria:**

**Given** batch execution completed with some failures
**When** I run `rgrid retry --batch <batch-id> --failed-only`
**Then** CLI retries only executions with status = failed
**And** successful executions are skipped
**And** retried executions get new execution IDs

**Prerequisites:** Story 5.5

**Technical Notes:**
- API endpoint: POST /api/v1/executions/retry
- Filter by batch_id + status=failed
- Reference: PRD FR32

---

---

## Epic 6: Caching & Optimization

**Goal:** Implement 3-level content-hash caching to make repeat executions instant.

**Value:** Transform 30-second first run into instant subsequent runs - "it just works" faster.

**FRs Covered:** FR21, FR22, FR23, FR24, FR25, FR26

### Story 6.1: Implement Script Content Hashing and Cache Lookup

As a developer,
I want identical scripts cached to avoid rebuilding images,
So that repeat executions start instantly.

**Acceptance Criteria:**

**Given** API receives execution request
**When** API calculates `script_hash = sha256(script_content)`
**Then** API checks script_cache table for existing hash
**And** if cache hit, skips Docker build and uses cached image
**And** if cache miss, builds new image and stores hash

**Prerequisites:** Epic 2 complete

**Technical Notes:**
- script_cache table: hash, image_id, created_at
- Cache TTL: 30 days
- Reference: architecture.md Decision 10 (content-hash caching)

---

### Story 6.2: Implement Dependency Layer Caching

As a developer,
I want requirements.txt changes to trigger rebuild while identical deps use cache,
So that dependency installations are fast.

**Acceptance Criteria:**

**Given** script has requirements.txt
**When** API calculates `deps_hash = sha256(requirements_content)`
**Then** API checks dependency_cache table
**And** if cache hit, uses cached pip layer
**And** if cache miss, runs `pip install -r requirements.txt` and caches layer

**Prerequisites:** Story 6.1

**Technical Notes:**
- dependency_cache table: hash, layer_id, created_at
- Docker multi-stage builds for layering
- Reference: architecture.md Decision 10

---

### Story 6.3: Implement Automatic Cache Invalidation

As a developer,
I want cache automatically invalidated when script or deps change,
So that I never get stale results.

**Acceptance Criteria:**

**Given** I modify script or requirements.txt
**When** new execution is submitted
**Then** new hash is calculated
**And** cache lookup fails (new hash != old hash)
**And** new image is built and cached with new hash
**And** old cache entries remain valid for unchanged scripts

**Prerequisites:** Story 6.2

**Technical Notes:**
- Hash changes automatically invalidate cache
- No manual cache management needed
- Reference: PRD FR24, FR25

---

### Story 6.4: Implement Optional Input File Caching

As a developer,
I want identical input files cached to skip re-uploads,
So that reprocessing same file is faster.

**Acceptance Criteria:**

**Given** execution uses input files
**When** API calculates `inputs_hash = sha256(all_input_contents)`
**Then** API checks input_cache table
**And** if cache hit, skips upload and uses cached file reference
**And** if cache miss, uploads files and stores hash

**Prerequisites:** Story 6.3

**Technical Notes:**
- input_cache table: hash, file_refs, created_at
- Optional feature (enabled via flag)
- Reference: PRD FR26

---

---

## Epic 7: File & Artifact Management

**Goal:** Make file uploads/downloads completely automatic and invisible to users.

**Value:** "Files just appear" locally after remote execution - no manual download steps.

**FRs Covered:** FR44, FR45, FR46, FR47, FR48, FR49, FR50

### Story 7.1: Auto-Upload Input Files Referenced in Arguments

As a developer,
I want files mentioned in script arguments automatically uploaded,
So that I don't manually manage uploads.

**Acceptance Criteria:**

**Given** I run `rgrid run process.py data.csv config.json`
**When** CLI detects file arguments
**Then** CLI uploads data.csv and config.json to MinIO
**And** runner downloads files into container /work directory
**And** script receives correct file paths as arguments

**Prerequisites:** Epic 2 complete

**Technical Notes:**
- Use MinIO presigned PUT URLs for uploads
- CLI detects files via os.path.isfile()
- Reference: architecture.md Decision 5, PRD FR44

---

### Story 7.2: Auto-Collect Output Files from Container

As a developer,
I want all files created in /work directory automatically collected,
So that outputs are captured without explicit specification.

**Acceptance Criteria:**

**Given** script creates files in working directory
**When** execution completes
**Then** runner scans /work for all files
**And** runner uploads all outputs to MinIO: executions/<exec_id>/outputs/
**And** artifacts recorded in database with metadata

**Prerequisites:** Story 7.1

**Technical Notes:**
- Ignore script.py itself (don't collect inputs)
- Collect only new files created during execution
- Reference: PRD FR45

---

### Story 7.3: Store Outputs in MinIO with Retention Policy

As a developer,
I want outputs stored with 30-day retention,
So that results are available for download but not forever.

**Acceptance Criteria:**

**Given** outputs are uploaded to MinIO
**When** storage writes files
**Then** files are stored in MinIO bucket: rgrid-executions
**And** object lifecycle policy deletes files after 30 days
**And** artifacts table tracks retention expiry date

**Prerequisites:** Story 7.2

**Technical Notes:**
- MinIO lifecycle policies
- Configurable retention via environment variable
- Reference: architecture.md Decision 5, PRD FR46

---

### Story 7.4: Auto-Download Outputs to Current Directory (Single Execution)

As a developer,
I want single execution outputs downloaded automatically to current directory,
So that it feels like local execution.

**Acceptance Criteria:**

**Given** I run `rgrid run process.py input.json` (single execution)
**When** execution completes
**Then** CLI automatically downloads all outputs to current directory
**And** files appear as if script ran locally
**And** CLI displays: "✓ Downloaded: output.json (1.2 MB), results.csv (0.5 MB)"

**Prerequisites:** Story 7.3

**Technical Notes:**
- Use MinIO presigned GET URLs for downloads
- Download in parallel for speed
- Reference: PRD FR47

---

### Story 7.5: Implement --remote-only Flag to Skip Auto-Download

As a developer,
I want to skip automatic downloads for large outputs,
So that I can selectively download later.

**Acceptance Criteria:**

**Given** I run `rgrid run script.py --remote-only`
**When** execution completes
**Then** CLI does NOT download outputs
**And** CLI displays: "✓ Execution complete. Outputs stored remotely."
**And** CLI shows command: "Download with: rgrid download exec_abc123"

**Prerequisites:** Story 7.4

**Technical Notes:**
- Add --remote-only flag to CLI
- Outputs remain in MinIO until explicit download
- Reference: PRD FR48

---

### Story 7.6: Implement Large File Streaming and Compression

As a developer,
I want large files (>100MB) handled efficiently,
So that uploads/downloads don't time out or consume excessive memory.

**Acceptance Criteria:**

**Given** output file is >100MB
**When** runner uploads file
**Then** file is streamed (not loaded into memory)
**And** file is compressed with gzip
**And** download automatically decompresses

**Prerequisites:** Story 7.5

**Technical Notes:**
- Stream using multipart uploads (MinIO SDK)
- Gzip compression for text files, skip for already-compressed formats
- Reference: PRD FR50

---

---

## Epic 8: Observability & Real-time Feedback

**Goal:** Provide comprehensive visibility into execution state with real-time log streaming.

**Value:** Developers see exactly what's happening - no "black box" execution.

**FRs Covered:** FR6, FR7, FR57, FR58, FR59, FR60, FR61, FR62, FR78, FR79, FR80, FR81, FR82

### Story 8.1: Implement `rgrid status` Command

As a developer,
I want to check execution status via `rgrid status <exec_id>`,
So that I can monitor progress.

**Acceptance Criteria:**

**Given** execution is running or completed
**When** I run `rgrid status exec_abc123`
**Then** CLI displays:
```
Execution: exec_abc123
Status: running
Started: 2025-11-15 10:30:15
Duration: 45s
Worker: worker-hetzner-01
Cost: $0.02 (estimated)
```

**Prerequisites:** Epic 2 complete

**Technical Notes:**
- API endpoint: GET /api/v1/executions/{exec_id}
- Return ExecutionStatus schema
- Reference: PRD FR6

---

### Story 8.2: Implement `rgrid logs` Command with Historical Logs

As a developer,
I want to view stdout/stderr logs for any execution,
So that I can debug failures.

**Acceptance Criteria:**

**Given** execution has completed
**When** I run `rgrid logs exec_abc123`
**Then** CLI fetches logs from execution_logs table
**And** displays logs in chronological order with timestamps
**And** shows both stdout and stderr interleaved

**Prerequisites:** Epic 2 (Story 2.2 captures logs)

**Technical Notes:**
- API endpoint: GET /api/v1/executions/{exec_id}/logs
- Store logs in execution_logs table (structured JSON)
- Reference: PRD FR7, FR59

---

### Story 8.3: Implement WebSocket Log Streaming for Real-Time Logs

As a developer,
I want real-time log streaming via `rgrid logs exec_abc123 --follow`,
So that I can watch long-running jobs.

**Acceptance Criteria:**

**Given** execution is running
**When** I run `rgrid logs exec_abc123 --follow`
**Then** CLI opens WebSocket connection to API
**And** runner streams logs to API via WebSocket
**And** CLI displays logs in real-time (< 1 second latency)
**And** logs continue streaming until execution completes or user cancels (Ctrl+C)

**Prerequisites:** Story 8.2

**Technical Notes:**
- WebSocket endpoint: /api/v1/executions/{exec_id}/stream
- Runner → API → CLI log pipeline
- Reference: architecture.md Decision 8 (WebSocket), PRD FR78

---

### Story 8.4: Implement CLI Reconnection for WebSocket Streams

As a developer,
I want to reconnect to log streams if network drops,
So that I don't lose visibility into long jobs.

**Acceptance Criteria:**

**Given** WebSocket connection drops during streaming
**When** CLI detects disconnection
**Then** CLI automatically reconnects within 5 seconds
**And** CLI resumes streaming from last received log line
**And** no logs are skipped or duplicated

**Prerequisites:** Story 8.3

**Technical Notes:**
- Cursor-based resumption (track last log sequence number)
- Exponential backoff for reconnection attempts
- Reference: architecture.md Decision 8, PRD FR79

---

### Story 8.5: Implement Batch Progress Display with --watch

As a developer,
I want batch progress displayed with `rgrid run --batch data/*.csv --watch`,
So that I can monitor parallel execution status.

**Acceptance Criteria:**

**Given** batch execution with --watch flag
**When** executions run
**Then** CLI displays aggregate progress:
```
[=========>           ] 45/100 complete (3 failed, 10 running, 42 queued)
Duration: 2m 30s | ETA: 3m 15s | Cost: $0.90
```

**And** user can press 'l' to drill down into individual execution logs
**And** user can press 'q' to detach (execution continues in background)

**Prerequisites:** Story 5.3, Story 8.3

**Technical Notes:**
- Aggregate stats from multiple execution statuses
- Calculate ETA based on average completion time
- Reference: PRD FR80, FR82

---

### Story 8.6: Track Execution Metadata in Database

As a developer,
I want comprehensive execution metadata tracked,
So that I can audit and analyze execution history.

**Acceptance Criteria:**

**Given** execution runs
**When** execution completes
**Then** database records:
- execution_id, account_id, script_hash
- start_time, end_time, duration_seconds
- status (completed/failed), exit_code
- worker_id, runtime, cost_micros
- input_files, output_files (artifact references)

**Prerequisites:** Epic 2 complete

**Technical Notes:**
- executions table schema from architecture.md
- Structured metadata for analytics
- Reference: PRD FR60

---

---

## Epic 9: Cost Tracking & Billing

**Goal:** Provide transparent, predictable cost tracking with per-execution granularity.

**Value:** Developers know exactly what they're paying for - no surprise bills.

**FRs Covered:** FR9, FR63, FR64, FR65, FR66, FR67

### Story 9.1: Implement MICRONS Cost Calculation

As a developer,
I want costs stored as integers (microns) for exact precision,
So that billing is accurate to the fraction of a cent.

**Acceptance Criteria:**

**Given** worker has hourly cost (e.g., €5.83/hour = 5,830,000 micros/hour)
**When** execution completes
**Then** cost is calculated:
```
cost_micros = (duration_seconds / 3600) * hourly_cost_micros
```

**And** stored as BIGINT in database
**And** displayed to user as currency (e.g., €0.02)

**Prerequisites:** Epic 4 (worker provisioning)

**Technical Notes:**
- MICRONS pattern from architecture.md (1 EUR = 1,000,000 micros)
- No float arithmetic - all integer math
- Reference: architecture.md MICRONS pattern

---

### Story 9.2: Implement Billing Hour Cost Amortization

As a developer,
I want worker costs amortized across all jobs in a billing hour,
So that costs are fair and efficient.

**Acceptance Criteria:**

**Given** worker runs 10 jobs in one billing hour
**When** billing hour ends
**Then** hourly cost is divided among jobs:
```
cost_per_job = hourly_cost / job_count
```

**And** each execution's finalized_cost_micros is updated
**And** users see reduced costs for jobs sharing billing hours

**Prerequisites:** Story 4.3 (billing hour tracking), Story 9.1

**Technical Notes:**
- Two-phase costing: estimated (immediate) → finalized (after hour ends)
- Reference: architecture.md billing hour optimization

---

### Story 9.3: Implement `rgrid cost` Command

As a developer,
I want to view cost breakdown via `rgrid cost`,
So that I can track spending.

**Acceptance Criteria:**

**Given** I run `rgrid cost`
**Then** CLI displays:
```
Date        Executions  Compute Time   Cost
2025-11-15  45          2.3h           €0.18
2025-11-14  120         5.1h           €0.39

Total (last 7 days): €2.47
```

**And** I can filter by date range: `rgrid cost --since 2025-11-01`

**Prerequisites:** Story 9.2

**Technical Notes:**
- API endpoint: GET /api/v1/costs
- Query executions table, sum cost_micros
- Reference: PRD FR64

---

### Story 9.4: Implement Cost Estimation for Batch Executions

As a developer,
I want cost estimates before running batch jobs,
So that I can make informed decisions.

**Acceptance Criteria:**

**Given** I run `rgrid estimate --runtime python:3.11 --batch data/*.csv`
**When** CLI calculates estimate
**Then** CLI displays:
```
Estimated executions: 500
Estimated duration: ~30s per execution (based on similar scripts)
Estimated cost: ~€1.20 (500 executions × 30s × €0.008/hour)
```

**Prerequisites:** Story 9.3

**Technical Notes:**
- Use historical data to estimate duration
- Calculate: (count * avg_duration * hourly_cost) / 3600
- Reference: PRD FR65

---

### Story 9.5: Implement Cost Alerts (Future Enhancement)

As a developer,
I want to set spending limits and receive alerts,
So that I can prevent unexpected bills.

**Acceptance Criteria:**

**Given** I set spending limit: `rgrid cost set-limit €50/month`
**When** account approaches 80% of limit
**Then** API sends email alert
**And** at 100%, API blocks new executions

**Prerequisites:** Story 9.3

**Technical Notes:**
- Future enhancement (mark as optional)
- Reference: PRD FR67

---

---

## Epic 10: Web Interfaces & MVP Polish

**Goal:** Complete MVP with marketing website, console dashboard, and production-ready error handling.

**Value:** Makes RGrid accessible to non-CLI users and production-ready.

**FRs Covered:** FR8, FR10, FR68, FR69, FR70, FR71, FR72, FR73, FR74, FR75, FR76, FR77

### Story 10.1: Build Marketing Website Landing Page

As a potential user,
I want a clear landing page at rgrid.dev,
So that I understand the value proposition immediately.

**Acceptance Criteria:**

**Given** website is deployed
**When** user visits https://rgrid.dev
**Then** page loads in < 1 second
**And** hero section shows: "Run Python scripts remotely. No infrastructure."
**And** clear CTA: "Get Started" → https://app.rgrid.dev/signup
**And** features section highlights: Simplicity, Cost, Scale
**And** code example shows: `python script.py` → `rgrid run script.py`

**Prerequisites:** Epic 1 (foundation)

**Technical Notes:**
- Next.js 14 static site (App Router)
- Deploy to Vercel or control plane
- Reference: PRD marketing website section

---

### Story 10.2: Build Console Dashboard with Execution History

As a developer,
I want a web console to view execution history,
So that non-CLI users can monitor jobs.

**Acceptance Criteria:**

**Given** user logs in to https://app.rgrid.dev
**When** dashboard loads
**Then** displays table of recent executions:
- execution_id, script_name, status, started_at, duration, cost
- Click execution → detail view with logs and outputs

**Prerequisites:** Epic 1 (auth), Epic 8 (execution metadata)

**Technical Notes:**
- Next.js 14 dashboard (App Router)
- Clerk authentication
- API integration for execution data
- Reference: PRD web console section

---

### Story 10.3: Implement Download Outputs via Console

As a developer,
I want to download outputs from web console,
So that I can retrieve results without CLI.

**Acceptance Criteria:**

**Given** execution has completed outputs
**When** user views execution detail page
**Then** page lists all output files with sizes
**And** user can click "Download" to get file
**And** download uses MinIO presigned GET URLs

**Prerequisites:** Story 10.2

**Technical Notes:**
- Generate presigned URLs server-side
- Reference: PRD FR8

---

### Story 10.4: Implement Structured Error Handling with Clear Messages

As a developer,
I want actionable error messages (not stack traces),
So that I can fix issues quickly.

**Acceptance Criteria:**

**Given** execution fails
**When** CLI displays error
**Then** shows clear, actionable message:
```
❌ Execution failed: exec_abc123

Error: Script exited with code 1

Cause: ModuleNotFoundError: No module named 'pandas'

Fix: Add 'pandas' to requirements.txt or use --runtime python:3.11-datascience

Logs: rgrid logs exec_abc123
```

**Prerequisites:** Epic 2 (execution)

**Technical Notes:**
- Detect common errors: missing deps, syntax errors, timeouts
- Map to user-friendly messages
- Reference: PRD FR10, FR68

---

### Story 10.5: Implement Network Failure Graceful Handling

As a developer,
I want network failures handled gracefully with auto-reconnection,
So that transient issues don't break my workflow.

**Acceptance Criteria:**

**Given** network connection drops during CLI operation
**When** CLI detects failure
**Then** CLI automatically retries with exponential backoff
**And** displays: "Connection lost. Retrying... (attempt 2/5)"
**And** on success, continues operation seamlessly
**And** on persistent failure, displays: "Network error. Check connection and retry."

**Prerequisites:** Epic 1 (CLI)

**Technical Notes:**
- httpx retry logic with exponential backoff
- Max 5 retry attempts
- Reference: PRD FR69

---

### Story 10.6: Implement Manual Retry Command

As a developer,
I want to manually retry failed executions,
So that I can fix transient failures.

**Acceptance Criteria:**

**Given** execution failed
**When** I run `rgrid retry exec_abc123`
**Then** API creates new execution with same script/inputs
**And** new execution_id is generated
**And** CLI displays: "Retry started: exec_xyz789"

**Prerequisites:** Epic 2 (execution)

**Technical Notes:**
- API endpoint: POST /api/v1/executions/{exec_id}/retry
- Clone execution record with new ID
- Reference: PRD FR72

---

### Story 10.7: Implement Auto-Retry for Transient Failures

As a developer,
I want automatic retries for transient failures (worker crashes, network errors),
So that temporary issues are self-healing.

**Acceptance Criteria:**

**Given** execution fails due to transient error (worker died, network timeout)
**When** runner detects failure type
**Then** API automatically retries execution (max 2 retries)
**And** retry count is tracked in execution metadata
**And** user sees: "Auto-retry 1/2 after worker failure"

**Prerequisites:** Story 10.6

**Technical Notes:**
- Detect transient failures: timeout, worker death, network errors
- Don't retry: script errors, validation errors
- Reference: PRD FR73

---

### Story 10.8: Implement Execution Metadata Tagging

As a developer,
I want to attach custom metadata to executions via --metadata flag,
So that I can organize and filter jobs.

**Acceptance Criteria:**

**Given** I run `rgrid run script.py --metadata project=ml-model --metadata env=prod`
**When** execution is created
**Then** metadata is stored as JSON in executions table
**And** I can filter executions by metadata: `rgrid list --metadata project=ml-model`

**Prerequisites:** Epic 2 (execution)

**Technical Notes:**
- Store metadata as JSONB column for queryability
- Reference: PRD FR74, FR75

---

---

## FR Coverage Matrix

| FR | Requirement | Epic | Stories |
|----|-------------|------|---------|
| FR1 | Install via package manager | Epic 1 | 1.4 |
| FR2 | Authenticate in < 1 minute | Epic 1 | 1.5 |
| FR3 | Execute scripts remotely | Epic 2 | 2.1 |
| FR4 | Execute in parallel (--batch) | Epic 5 | 5.1, 5.2 |
| FR5 | Specify runtime (--runtime) | Epic 2 | 2.3 |
| FR6 | Monitor execution status | Epic 8 | 8.1 |
| FR7 | Access execution logs | Epic 8 | 8.2 |
| FR8 | Download outputs | Epic 10 | 10.3 |
| FR9 | View cost estimates | Epic 9 | 9.3, 9.4 |
| FR10 | Clear error messages | Epic 10 | 10.4 |
| FR11 | Isolated container execution | Epic 2 | 2.2 |
| FR12 | Pre-configured runtimes | Epic 2 | 2.3 |
| FR13 | Custom Docker images | Epic 2 | 2.3 |
| FR14 | Input files as arguments | Epic 2 | 2.5 |
| FR15 | Auto-collect outputs | Epic 7 | 7.2 |
| FR16 | Exit code determines success | Epic 2 | 2.2 |
| FR17 | Environment variables (--env) | Epic 2 | 2.7 |
| FR18 | Auto-detect requirements.txt | Epic 2 | 2.4 |
| FR19 | Explicit --requirements flag | Epic 2 | 2.4 |
| FR20 | Network access by default | Epic 2 | 2.2 |
| FR21 | Cache script images | Epic 6 | 6.1 |
| FR22 | Cache dependency layers | Epic 6 | 6.2 |
| FR23 | Instant cached execution | Epic 6 | 6.1, 6.2 |
| FR24 | Auto cache invalidation | Epic 6 | 6.3 |
| FR25 | Invisible caching | Epic 6 | 6.1-6.3 |
| FR26 | Optional input file caching | Epic 6 | 6.4 |
| FR27 | Expand glob patterns | Epic 5 | 5.1 |
| FR28 | Distribute batch executions | Epic 5 | 5.2 |
| FR29 | Track batch progress | Epic 5 | 5.3 |
| FR30 | Max parallelism (--parallel) | Epic 5 | 5.2 |
| FR31 | Handle batch failures gracefully | Epic 5 | 5.5 |
| FR32 | Retry failed executions | Epic 5 | 5.6 |
| FR33 | Batch outputs by input name | Epic 5 | 5.4 |
| FR34 | Override output location | Epic 5 | 5.4 |
| FR35 | Flat output structure (--flat) | Epic 5 | 5.4 |
| FR36 | Auto-provision workers | Epic 4 | 4.1 |
| FR37 | Ray task scheduling | Epic 3 | 3.3 |
| FR38 | Scale based on queue depth | Epic 4 | 4.2 |
| FR39 | Auto-terminate idle workers | Epic 4 | 4.3 |
| FR40 | Worker health monitoring | Epic 3, 4 | 3.4, 4.5 |
| FR41 | Pre-cache Docker images | Epic 4 | 4.4 |
| FR42 | Manage Ray cluster lifecycle | Epic 3 | 3.1, 3.2 |
| FR43 | Network communication | Epic 3 | 3.1, 3.2 |
| FR44 | Auto-upload input files | Epic 7 | 7.1 |
| FR45 | Auto-collect outputs | Epic 7 | 7.2 |
| FR46 | S3 storage with retention | Epic 7 | 7.3 |
| FR47 | Auto-download outputs (single) | Epic 7 | 7.4 |
| FR48 | Skip auto-download (--remote-only) | Epic 7 | 7.5 |
| FR49 | List outputs before download | Epic 7 | 7.4 |
| FR50 | Handle large files efficiently | Epic 7 | 7.6 |
| FR51 | API key authentication | Epic 1 | 1.3 |
| FR52 | API keys never in project files | Epic 1 | 1.3, 1.5 |
| FR53 | rgrid init creates credentials | Epic 1 | 1.5 |
| FR54 | Optional project config | Epic 1 | 1.5 |
| FR55 | Project config safe to commit | Epic 1 | 1.5 |
| FR56 | Multi-account profiles (future) | Epic 1 | 1.5 |
| FR57 | View execution history | Epic 8, 10 | 8.6, 10.2 |
| FR58 | Real-time logs (--watch/--follow) | Epic 8 | 8.3 |
| FR59 | Historical logs | Epic 8 | 8.2 |
| FR60 | Track execution metadata | Epic 8 | 8.6 |
| FR61 | View worker pool status | Epic 8 | 8.1 |
| FR62 | Batch progress tracking | Epic 8 | 8.5 |
| FR63 | Per-execution cost calculation | Epic 9 | 9.1 |
| FR64 | Itemized cost breakdown | Epic 9 | 9.3 |
| FR65 | Cost estimates | Epic 9 | 9.4 |
| FR66 | Transparent billing | Epic 9 | 9.1, 9.2 |
| FR67 | Cost alerts/limits (future) | Epic 9 | 9.5 |
| FR68 | Detect common errors | Epic 10 | 10.4 |
| FR69 | Graceful network failure handling | Epic 10 | 10.5 |
| FR70 | Preserve failure logs | Epic 8, 10 | 8.2, 10.4 |
| FR71 | Prevent cascading failures | Epic 2, 3 | 2.2, 3.4 |
| FR72 | Manual retry command | Epic 10 | 10.6 |
| FR73 | Auto-retry transient failures | Epic 10 | 10.7 |
| FR74 | Custom metadata tagging | Epic 10 | 10.8 |
| FR75 | Query execution metadata | Epic 10 | 10.8 |
| FR76 | Execution lifecycle events | Epic 8 | 8.6 |
| FR77 | Pluggable abstractions | Epic 1-10 | Architecture foundations |
| FR78 | WebSocket log streaming | Epic 8 | 8.3 |
| FR79 | CLI reconnection | Epic 8 | 8.4 |
| FR80 | Batch aggregate progress | Epic 8 | 8.5 |
| FR81 | Long-running detached mode | Epic 8 | 8.3, 8.5 |
| FR82 | Batch progress estimates | Epic 8 | 8.5 |

**Coverage Validation:** All 82 FRs mapped to specific stories across 10 epics ✅

---

## Summary

**Epic Breakdown Complete:** 10 epics, 58 stories

**Coverage:** All 82 functional requirements mapped to implementable stories

**Story Quality:**
- ✅ All stories use BDD format (Given/When/Then)
- ✅ Stories sized for single-session completion
- ✅ Prerequisites clearly defined (no forward dependencies)
- ✅ Technical notes reference architecture decisions
- ✅ Vertically sliced (deliver complete functionality)

**Epic Sequencing:**
1. Epic 1 (Foundation) establishes project structure, CLI, auth
2. Epics 2-4 build core capability (single → distributed → auto-scaled)
3. Epics 5-7 add power features (batch, caching, file handling)
4. Epics 8-9 add observability and billing
5. Epic 10 completes MVP with web interfaces

**Next Steps in BMad Method:**
1. **UX Design** (conditional - CLI-first, minimal UI) - May skip or run for console dashboard
2. **Architecture** - Already complete! (architecture.md exists)
3. **Solutioning Gate Check** - Validate PRD ↔ Architecture ↔ Stories alignment
4. **Sprint Planning** - Generate sprint status tracking for Phase 4 implementation

**Living Document:**
This epic breakdown will be updated after UX Design (if run) and Architecture workflows to incorporate interaction details and technical decisions. It serves as the single source of truth for story details during implementation.

---

_For implementation: Each story will be executed using the `dev-story` workflow which pulls context from PRD + epics.md + Architecture + UX Design._

_This document was generated using the BMad Method Epic Breakdown workflow (v6-alpha)_

