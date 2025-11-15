# Epic Technical Specification: Single Script Execution

Date: 2025-11-15
Author: BMad
Epic ID: 2
Status: Draft

---

## Overview

Epic 2 establishes the core execution paradigm of RGrid: enabling developers to run Python scripts remotely with zero code changes. This epic proves the fundamental value proposition - transforming `python script.py` into `rgrid run script.py` while maintaining identical behavior. The implementation focuses on Docker-based container isolation, runtime environment management, dependency installation, file I/O handling, and environment variable support.

This epic builds directly upon Epic 1 (Foundation & CLI Core), leveraging the established CLI framework, API authentication, and FastAPI backend to create the complete single-script execution flow from CLI submission through containerized execution to output collection.

## Objectives and Scope

**In Scope:**
- Basic `rgrid run` command implementation (CLI → API → execution record)
- Docker container execution with isolation and security constraints
- Pre-configured runtime images (Python 3.10, 3.11, datascience, LLM, ffmpeg, Node.js)
- Automatic dependency detection and installation from requirements.txt
- Input file handling (upload, mount, pass as arguments)
- Output file collection and storage
- Environment variable injection via --env flag
- Container sandboxing (no network by default, read-only root filesystem)
- Exit code-based success determination

**Out of Scope:**
- Distributed execution across multiple workers (Epic 3)
- Batch/parallel execution (Epic 5)
- Caching and optimization (Epic 6)
- Real-time log streaming (Epic 8)
- Cost tracking (Epic 9)
- Auto-provisioning of infrastructure (Epic 4)

## System Architecture Alignment

**Components Involved:**
- **CLI (cli/)**: Implements `rgrid run` command, handles file uploads, submits execution requests
- **API (api/)**: Receives execution requests, creates execution records, interfaces with storage
- **Runner (runner/)**: Executes Docker containers, manages script lifecycle, handles I/O operations
- **Storage (MinIO)**: Stores uploaded input files and collected output artifacts
- **Database (Postgres)**: Tracks execution records, artifacts, logs

**Architecture Constraints:**
- Container isolation enforced via Docker security features (no network, read-only root, cgroup limits)
- Runner handles all uploads/downloads (not containers) per Decision 5
- Docker images follow pre-configured runtime pattern per Decision 4
- File I/O uses MinIO presigned URLs per Decision 5
- All operations follow async patterns for API scalability

**Cross-Epic Dependencies:**
- Requires Epic 1: CLI framework, API authentication, FastAPI backend, database schema
- Enables Epic 3: Provides base execution logic for Ray task distribution
- Enables Epic 5: Single execution is foundation for batch operations

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **CLI Runner Module** (`cli/rgrid/commands/run.py`) | Parse arguments, detect files, upload inputs, submit execution request | Script path, args, flags (--runtime, --env) | Execution ID, status display | CLI Team |
| **API Execution Service** (`api/services/execution.py`) | Create execution record, validate inputs, generate presigned URLs | ExecutionCreate schema (script, args, runtime, env) | Execution record, execution_id | API Team |
| **Runner Executor** (`runner/executor.py`) | Claim job, run Docker container, capture logs, collect outputs | Execution record from database | Updated execution status, logs, artifacts | Runner Team |
| **Storage Service** (`api/services/storage.py`) | Generate presigned URLs for MinIO, manage artifact metadata | File paths, execution_id | Presigned URLs (PUT/GET) | API Team |
| **Container Manager** (`runner/container.py`) | Docker SDK wrapper, enforce security constraints, mount volumes | Runtime image, script, args, env vars | Container exit code, stdout/stderr | Runner Team |

### Data Models and Contracts

**Execution Record (Postgres `executions` table):**
```python
class Execution(Base):
    __tablename__ = "executions"

    execution_id: str  # Primary key, format: exec_{uuid}
    account_id: str    # Foreign key to accounts
    script_content: str  # Python script source code
    script_hash: str   # SHA256 hash (for Epic 6 caching)
    runtime: str       # e.g., "python:3.11", "python:3.11-datascience"
    args: List[str]    # Command-line arguments (JSON array)
    env_vars: Dict[str, str]  # Environment variables (JSON object)

    status: str        # queued|running|completed|failed
    exit_code: int     # Container exit code (0 = success)

    created_at: datetime
    started_at: datetime
    completed_at: datetime

    worker_id: str     # Which worker executed (null for Epic 2)
    cost_micros: int   # Execution cost in microns (Epic 9)
```

**Artifact Record (Postgres `artifacts` table):**
```python
class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: str     # Primary key
    execution_id: str    # Foreign key to executions
    artifact_type: str   # "input" | "output"
    filename: str        # Original filename
    file_path: str       # MinIO object key: executions/{exec_id}/inputs|outputs/{filename}
    size_bytes: int
    content_type: str    # MIME type
    created_at: datetime
```

**API Request/Response Models:**
```python
# POST /api/v1/executions
class ExecutionCreate(BaseModel):
    script_content: str
    script_filename: str  # e.g., "process.py"
    runtime: str = "python:3.11"  # Default runtime
    args: List[str] = []
    env_vars: Dict[str, str] = {}
    input_files: List[str] = []  # Filenames to upload

class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    created_at: datetime
    upload_urls: Dict[str, str]  # {filename: presigned_put_url}
```

### APIs and Interfaces

**CLI → API**
```
POST /api/v1/executions
Authorization: Bearer {api_key}
Content-Type: application/json

Request Body:
{
  "script_content": "import sys\nprint(f'Hello {sys.argv[1]}')",
  "script_filename": "hello.py",
  "runtime": "python:3.11",
  "args": ["world"],
  "env_vars": {"DEBUG": "true"},
  "input_files": ["data.csv"]
}

Response (200 OK):
{
  "execution_id": "exec_abc123def456",
  "status": "queued",
  "created_at": "2025-11-15T10:30:00Z",
  "upload_urls": {
    "data.csv": "https://minio:9000/executions/exec_abc123/inputs/data.csv?X-Amz-..."
  }
}

Error Codes:
- 400: Invalid request (missing script_content, invalid runtime)
- 401: Unauthorized (invalid API key)
- 413: Payload too large (script >10MB)
- 500: Internal server error
```

**Runner → Storage**
```
# Runner uses presigned URLs from execution metadata
# No direct API calls needed for file operations

# Upload outputs after execution:
GET /api/v1/executions/{exec_id}/presigned-output-urls
Authorization: Internal (runner service token)

Response:
{
  "urls": {
    "output.json": "https://minio:9000/executions/exec_abc123/outputs/output.json?..."
  }
}
```

**Container Execution Interface:**
```python
# runner/executor.py
async def execute_script(execution_id: str) -> ExecutionResult:
    """
    Execute script in Docker container.

    Args:
        execution_id: Unique execution identifier

    Returns:
        ExecutionResult with exit_code, stdout, stderr, artifacts

    Raises:
        ContainerError: If container fails to start or crashes
        TimeoutError: If execution exceeds timeout (Epic 2: no timeout, added in Epic 8)
    """
    # 1. Load execution record from database
    # 2. Download input files from MinIO to /tmp/{exec_id}/inputs/
    # 3. Create container with runtime image
    # 4. Mount /tmp/{exec_id} as /work in container
    # 5. Execute: python /work/script.py {args}
    # 6. Capture stdout/stderr
    # 7. Collect all files in /work (except script.py)
    # 8. Upload outputs to MinIO
    # 9. Update execution record with status, exit_code
```

### Workflows and Sequencing

**End-to-End Execution Flow:**

```
1. USER: rgrid run process.py data.csv --runtime python:3.11 --env API_KEY=abc

2. CLI:
   a. Read process.py content
   b. Detect data.csv is a file (os.path.isfile)
   c. Load ~/.rgrid/credentials for API key
   d. POST /api/v1/executions with script_content, args, runtime, env_vars, input_files
   e. Receive execution_id and upload_urls
   f. Upload data.csv to presigned URL (PUT request)
   g. Display: "Execution started: exec_abc123"

3. API:
   a. Validate request (check script_content exists, runtime valid)
   b. Authenticate via API key dependency injection
   c. Calculate script_hash = sha256(script_content)
   d. Create execution record in database (status=queued)
   e. Generate presigned PUT URLs for input files
   f. Return execution_id and upload_urls
   g. [Epic 3] Submit to Ray queue (Epic 2: direct runner invocation)

4. RUNNER:
   a. Query database for next queued execution (Epic 2: polling, Epic 3: Ray task)
   b. Update status=running, started_at=now()
   c. Download input files from MinIO to /tmp/{exec_id}/inputs/
      - Use artifact records to find file paths
      - Generate presigned GET URLs
   d. Write script_content to /tmp/{exec_id}/script.py
   e. Create Docker container:
      - Image: python:3.11-slim
      - Volume: /tmp/{exec_id} → /work (read-write)
      - Network: none (--network none)
      - Env: API_KEY=abc, DEBUG=true
      - Root filesystem: read-only except /work
      - Resource limits: --memory 2g --cpus 1
   f. Execute: python /work/script.py /work/inputs/data.csv
   g. Stream stdout/stderr to logs (store in memory for Epic 2, Epic 8 adds DB storage)
   h. Wait for container exit
   i. Capture exit_code
   j. Scan /work for output files (exclude script.py, inputs/)
   k. Upload outputs to MinIO: executions/{exec_id}/outputs/
   l. Create artifact records for each output
   m. Update execution: status=completed|failed, exit_code, completed_at

5. CLI (future enhancement - Epic 8):
   - Poll for status or stream logs
   - Auto-download outputs when complete

Exit Code Semantics:
- 0: Success
- 1-255: Script error (propagate container exit code)
- -1: Runner error (container failed to start)
- -2: Timeout (Epic 8)
```

**Sequence Diagram (Text):**
```
User → CLI: rgrid run script.py arg1
CLI → API: POST /executions {script, args, runtime}
API → DB: INSERT execution (status=queued)
API → CLI: {exec_id, upload_urls}
CLI → MinIO: PUT input files (presigned URL)
CLI → User: "Execution started: exec_123"

Runner → DB: SELECT queued execution
Runner → MinIO: GET input files
Runner → Docker: Create container, run script
Docker → Runner: exit_code, stdout, stderr
Runner → MinIO: PUT output files
Runner → DB: UPDATE execution (status=completed)
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Cold start latency**: < 30 seconds from `rgrid run` to script execution start
  - Breakdown: API request (200ms) + input upload (5s for 10MB) + Docker pull (20s if not cached) + container start (2s)
- **Warm start latency**: < 5 seconds (pre-pulled images, no upload)
- **API response time**: < 500ms for execution submission (excludes file upload)
- **Container startup**: < 2 seconds (Docker overhead)
- **Database query time**: < 100ms for execution record operations
- **File upload/download**: Minimum 10 MB/s (limited by network, not application)

**Scalability:**
- Single runner can handle **2 concurrent executions** (Epic 2 scope: 1 runner)
- Epic 3 scales to N runners
- API designed for 100 req/s throughput (async FastAPI)

**Source:** Architecture NFRs, PRD performance requirements

### Security

**Authentication & Authorization:**
- All API requests require valid API key in Authorization header (implemented in Epic 1)
- API keys stored as bcrypt hashes (never plaintext)
- Execution records scoped to account_id (tenant isolation)

**Container Sandboxing:**
- **Network isolation**: Containers run with `--network none` by default (no internet access)
  - Prevents data exfiltration, unauthorized external calls
  - Future: Epic 2 adds `--network` flag to enable networking per-execution
- **Filesystem isolation**: Root filesystem read-only, only /work is writable
  - Prevents container escape, system file modification
- **Resource limits**: cgroup constraints (--memory 2g --cpus 1)
  - Prevents resource exhaustion DoS
- **No privileged mode**: Containers run as non-root user (future hardening)

**Data Handling:**
- Input/output files encrypted at rest in MinIO (server-side encryption)
- Presigned URLs expire after 1 hour
- Environment variables with secrets not logged (avoid stdout/stderr leakage)

**Source:** Architecture Decision 2 (container isolation), PRD security section

### Reliability/Availability

**Error Handling:**
- Script failures (non-zero exit codes) recorded but don't crash runner
- Container crashes detected, execution marked as failed
- Database connection failures: API returns 503, runner retries with exponential backoff
- MinIO connection failures: Runner retries upload/download 3 times before failing

**Execution Guarantees:**
- **At-most-once**: Epic 2 does not guarantee retry (Epic 10 adds auto-retry)
- Failed executions preserve logs and error context in database
- Partial outputs (container crashed mid-execution) still uploaded if files exist

**Degradation:**
- If MinIO unavailable: API rejects new executions (fail fast)
- If database unavailable: API returns 503, CLI shows clear error message

**Source:** Architecture reliability patterns, PRD FR68-FR73

### Observability

**Logging:**
- **API logs**: All execution submissions, authentication events (JSON structured logs)
- **Runner logs**: Execution start/stop, container lifecycle, upload/download events
- **Container logs**: stdout/stderr captured and stored in execution_logs table (Epic 8)
  - Epic 2: Stored in memory during execution, written to DB on completion
  - Retention: 30 days

**Metrics:**
- Execution count (total, by status: completed/failed)
- Execution duration (p50, p95, p99)
- Container startup time
- API response times

**Tracing:**
- Epic 2: Basic execution_id propagation through logs
- Epic 8: Distributed tracing with OpenTelemetry

**Required Signals:**
- Execution status changes (queued → running → completed/failed)
- File upload/download success/failure
- Container exit codes
- API authentication failures

**Source:** Architecture observability requirements, PRD FR57-FR62

## Dependencies and Integrations

**Language/Runtime:**
- Python 3.11+ (API, orchestrator, runner, CLI)

**Core Dependencies (pyproject.toml - API):**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"        # Web framework
uvicorn = "^0.24.0"         # ASGI server
sqlalchemy = "^2.0.23"      # ORM (async)
asyncpg = "^0.29.0"         # Postgres driver
pydantic = "^2.5.0"         # Data validation
boto3 = "^1.29.0"           # MinIO S3 client
bcrypt = "^4.1.0"           # API key hashing
```

**Core Dependencies (pyproject.toml - Runner):**
```toml
[tool.poetry.dependencies]
python = "^3.11"
docker = "^7.0.0"           # Docker SDK for container management
boto3 = "^1.29.0"           # MinIO client
sqlalchemy = "^2.0.23"      # Database queries
asyncpg = "^0.29.0"
aiohttp = "^3.9.0"          # Async HTTP for API calls
```

**Core Dependencies (pyproject.toml - CLI):**
```toml
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1.0"            # CLI framework
httpx = "^0.25.0"           # HTTP client (async support for Epic 8)
pydantic = "^2.5.0"         # Response parsing
rich = "^13.7.0"            # Terminal formatting
```

**External Services:**
- **PostgreSQL 15+**: Primary database
  - Required tables: executions, artifacts, accounts, api_keys (Epic 1)
- **MinIO**: S3-compatible object storage
  - Bucket: `rgrid-executions`
  - Lifecycle policy: 30-day retention
- **Docker Engine 24+**: Container runtime (on runner nodes)
  - Required for Docker SDK

**Docker Images (Pre-configured Runtimes):**
- `python:3.10-slim` (official)
- `python:3.11-slim` (official)
- Custom images (built in infra/dockerfiles/):
  - `rgrid/python:3.11-datascience` (numpy, pandas, scikit-learn)
  - `rgrid/python:3.11-llm` (openai, anthropic, langchain)
  - `rgrid/ffmpeg:latest` (ffmpeg + Python)
  - `node:20-slim` (official Node.js)

**Integration Points:**
- CLI → API: REST over HTTPS
- API → Database: asyncpg connection pool
- API → MinIO: boto3 client with presigned URLs
- Runner → Docker: Docker SDK (docker.from_env())
- Runner → MinIO: boto3 client
- Runner → Database: asyncpg

**Version Constraints:**
- PostgreSQL: >= 15.0 (uses SKIP LOCKED for job claiming in Epic 3)
- MinIO: >= RELEASE.2023-11-01 (presigned URL support)
- Docker: >= 24.0 (security features)

## Acceptance Criteria (Authoritative)

**AC-2.1: Basic rgrid run Command**
1. When I run `rgrid run script.py arg1 arg2`, the CLI submits an execution request to the API
2. The API returns an execution_id in format `exec_{uuid}`
3. The CLI displays "Execution started: {execution_id}"

**AC-2.2: Docker Container Execution**
1. Scripts execute in isolated Docker containers with specified runtime
2. Containers have no network access by default (`--network none`)
3. Container root filesystem is read-only except /work directory
4. stdout and stderr are captured to logs
5. Container exit code determines execution success (0=success, non-zero=failure)

**AC-2.3: Pre-Configured Runtimes**
1. Runtime flag `--runtime python:3.11` uses python:3.11-slim image
2. Supported runtimes: python:3.10, python:3.11, python:3.11-datascience, python:3.11-llm, ffmpeg:latest, node:20
3. Images are pre-pulled during runner initialization (Epic 4 worker provisioning)

**AC-2.4: Auto-Detect Dependencies**
1. If script directory contains requirements.txt, runner installs dependencies via `pip install -r requirements.txt`
2. Dependencies are installed before script execution
3. If requirements.txt is missing, script runs with base image packages only

**AC-2.5: Handle Input Files**
1. When I run `rgrid run process.py input.csv`, the CLI uploads input.csv to MinIO
2. Runner downloads input.csv into container /work directory
3. Script receives /work/input.csv as argument and can read it normally

**AC-2.6: Collect Output Files**
1. All files created in container /work directory are collected after script completion
2. Outputs are uploaded to MinIO under executions/{exec_id}/outputs/
3. Artifact records are created in database with filename, size, content_type

**AC-2.7: Environment Variables**
1. When I run `rgrid run script.py --env API_KEY=abc --env DEBUG=true`, environment variables are set in container
2. Script can access variables via os.environ['API_KEY']
3. Environment variables are stored in execution record (encrypted if sensitive - future enhancement)

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-2.1 | APIs: POST /executions | CLI run.py, API execution service | Submit execution via CLI, verify API returns exec_id in correct format |
| AC-2.2 | Container Manager, Workflows | runner/executor.py, Docker SDK | Run script that attempts network access (should fail), verify exit code captured |
| AC-2.3 | Services: Container Manager | runner/container.py | Execute script with each runtime, verify correct image used |
| AC-2.4 | Workflows: Step 4-Runner | runner/executor.py | Create script with requirements.txt (pandas), verify pandas importable |
| AC-2.5 | APIs: Presigned URLs, Workflows | CLI run.py, runner/executor.py, storage service | Run script with CSV arg, verify file accessible at /work/input.csv |
| AC-2.6 | Workflows: Step 4-Runner | runner/executor.py, artifacts table | Script creates output.json, verify uploaded to MinIO and artifact record exists |
| AC-2.7 | Container Manager, Data Models | runner/container.py, executions.env_vars | Script prints os.environ, verify --env values present |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Docker image pull times (20+ seconds) could exceed cold start target
   - **Mitigation**: Pre-pull images during runner init (Epic 4), implement image caching (Epic 6)
2. **R2**: Large input files (>1GB) may timeout during upload
   - **Mitigation**: Epic 7 implements streaming and compression, Epic 2 accepts risk
3. **R3**: Container escapes could compromise runner host
   - **Mitigation**: Enforce security constraints (no network, read-only root, non-root user in future)
4. **R4**: Malicious scripts could exhaust runner resources (CPU/memory bombs)
   - **Mitigation**: cgroup limits enforced, add timeout in Epic 8

**Assumptions:**
1. **A1**: Runner has Docker daemon installed and accessible
2. **A2**: MinIO is always available (no offline mode in Epic 2)
3. **A3**: Scripts are trusted (no sandboxing beyond container isolation in Epic 2)
4. **A4**: Single runner can handle execution load (Epic 3 adds distributed execution)
5. **A5**: Users accept 30-second cold start latency for first execution

**Open Questions:**
1. **Q1**: Should we support Docker Compose for multi-container scripts?
   - **Decision**: No, out of scope for MVP (single container only)
2. **Q2**: How to handle scripts that require GPU access?
   - **Decision**: Defer to post-MVP (requires --gpus flag, special instance types)
3. **Q3**: Should we allow custom Dockerfile instead of pre-configured runtimes?
   - **Decision**: Future enhancement, Epic 2 uses pre-configured images only
4. **Q4**: What's the maximum script size?
   - **Decision**: 10 MB limit (API validation), should be sufficient for MVP

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests** (pytest, 80% coverage minimum)
   - CLI: Command parsing, file detection, API client mocking
   - API: Request validation, presigned URL generation, execution record creation
   - Runner: Container creation, file upload/download, log capture

2. **Integration Tests**
   - CLI → API: End-to-end execution submission
   - API → Database: Execution record persistence
   - Runner → Docker: Container lifecycle (create, execute, cleanup)
   - Runner → MinIO: File upload/download with presigned URLs

3. **End-to-End Tests**
   - Complete flow: `rgrid run script.py` → execution → output collection
   - Test cases:
     - Simple script (print hello world)
     - Script with requirements.txt (import pandas)
     - Script with input file (read CSV, process, write JSON)
     - Script with environment variables
     - Script that fails (non-zero exit code)
     - Script with no outputs (verify no artifacts created)

**Frameworks:**
- **Python**: pytest, pytest-asyncio, pytest-mock
- **Docker**: docker-py test helpers, container cleanup fixtures
- **Database**: pytest-postgresql (ephemeral test database)
- **Storage**: MinIO testcontainer or localstack

**Coverage of ACs:**
- Each AC mapped to specific test case(s)
- AC-2.1: CLI integration test
- AC-2.2: Runner unit test + E2E test
- AC-2.3: Runner integration test (each runtime)
- AC-2.4: E2E test with requirements.txt
- AC-2.5: E2E test with input file
- AC-2.6: E2E test with output files
- AC-2.7: E2E test with --env flag

**Edge Cases:**
- Empty script (should fail validation)
- Script with syntax errors (should fail with exit code 1)
- Script that creates no outputs (valid, no artifacts)
- Input file doesn't exist (CLI should error before upload)
- MinIO unavailable during output upload (runner retries, then fails execution)
- Container crashes mid-execution (capture partial outputs if any)

**Performance Tests:**
- Measure cold start latency (target: <30s)
- Measure API response time (target: <500ms)
- Measure container startup time (target: <2s)
- Test with 10MB input file upload

**Mocking Strategy:**
- CLI tests: Mock httpx client (API calls)
- API tests: Mock boto3 (MinIO), asyncpg (database)
- Runner tests: Mock Docker SDK for unit tests, real containers for integration tests

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 2.1
