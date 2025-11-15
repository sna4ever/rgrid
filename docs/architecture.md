# RGrid Architecture Document

**Version:** 1.0
**Date:** 2025-11-15
**Status:** Final - Ready for Implementation
**Track:** BMad Method - Greenfield

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Decisions](#architecture-decisions)
4. [Database Schema](#database-schema)
5. [Component Architecture](#component-architecture)
6. [Deployment Architecture](#deployment-architecture)
7. [Security Architecture](#security-architecture)
8. [Implementation Guidelines](#implementation-guidelines)
9. [Future Evolution Paths](#future-evolution-paths)

---

## Executive Summary

RGrid is a distributed compute platform for running Python scripts remotely with zero code changes. This document defines the complete technical architecture for MVP deployment on Hetzner infrastructure.

### Key Architectural Principles

1. **Convention Over Configuration** - Scripts run remotely identical to local execution
2. **LLM-Agent Friendly** - Clear structure, explicit types, pure functions
3. **Cost Optimization** - Maximize worker utilization within billing hours
4. **Shared Worker Pool** - Workers serve all accounts (not siloed)
5. **Multi-Tenant from Day 1** - Account-based billing following Jumpstart pattern
6. **Future-Proof Abstractions** - EMA, CPAL, runtime plugins ready for extension

### Technology Stack (MVP)

- **Backend Language:** Python 3.11+
- **API Framework:** FastAPI (async)
- **Web Framework:** Next.js 14+ (App Router)
- **Database:** PostgreSQL 15 (via Supabase or self-hosted)
- **Object Storage:** MinIO (S3-compatible)
- **Distributed Computing:** Ray
- **Container Runtime:** Docker
- **Cloud Provider:** Hetzner (control plane CX31, workers CX22)
- **Authentication:** Clerk (web) + API Keys (CLI)
- **Payments:** Stripe
- **Reverse Proxy:** Nginx

### Cost Structure

- **Fixed Costs:** €7.45/month (CX31 control plane + domain)
- **Variable Costs:** €0.005/hour per CX22 worker (auto-scaled)
- **Target Total:** ~€15/month for moderate usage (100 jobs/day)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ User's Machine                                              │
│  └─ rgrid CLI (Python + Click)                             │
│     └─ ~/.rgrid/credentials (API key)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS + API Key
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Hetzner Control Plane (CX31 - €6.45/mo)                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ FastAPI      │  │ Ray Head     │  │ PostgreSQL   │     │
│  │ (API Server) │  │ (Scheduler)  │  │ (Database)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
│         │                  │                                │
│  ┌──────┴──────────────────┴───────┐  ┌──────────────┐     │
│  │ MinIO (S3 Storage)              │  │ Docker       │     │
│  │  - Scripts, inputs, outputs     │  │ Registry     │     │
│  └─────────────────────────────────┘  └──────────────┘     │
│                                                             │
│  Private IP: 10.0.0.1 (Hetzner private network)            │
└────────────────────────┬────────────────────────────────────┘
                         │ Ray cluster connection
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Worker Pool (Hetzner CX22 - €0.005/hr, ephemeral)         │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Worker 1     │  │ Worker 2     │  │ Worker N     │     │
│  │ - Ray worker │  │ - Ray worker │  │ - Ray worker │     │
│  │ - Docker     │  │ - Docker     │  │ - Docker     │     │
│  │ - 2 CPU/4GB  │  │ - 2 CPU/4GB  │  │ - 2 CPU/4GB  │     │
│  │ - Max 2 jobs │  │ - Max 2 jobs │  │ - Max 2 jobs │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  Lifecycle: ~60 min (maximize billing hour utilization)    │
│  Auto-scaled based on queue depth + smart provisioning     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User runs: rgrid run script.py input.json
   ↓
2. CLI uploads script + input to MinIO (via presigned URL)
   ↓
3. CLI creates execution via API (POST /v1/executions)
   ↓
4. API calculates script_hash, checks cache, queues execution
   ↓
5. Ray scheduler assigns execution to available worker
   ↓
6. Worker downloads script, builds/pulls Docker image, executes
   ↓
7. Worker streams logs back via WebSocket to CLI (optional)
   ↓
8. Worker uploads outputs to MinIO
   ↓
9. API marks execution complete, finalizes cost
   ↓
10. CLI downloads outputs automatically
```

---

## Architecture Decisions

### Decision 1: Project Structure & Monorepo Layout ✅

**Decision:** Monorepo with shared Python package for common code.

**Rationale:**
- Atomic changes across CLI + API + orchestrator
- Shared type definitions prevent drift
- Easier development and testing
- Single CI/CD pipeline

**Structure:**

```
rgrid/
├── pyproject.toml           # Root monorepo config
├── rgrid_common/            # Shared code (types, Money class, utils)
│   ├── __init__.py
│   ├── models.py            # Pydantic models shared across services
│   ├── money.py             # Money class (micros handling)
│   └── types.py             # Type definitions
├── cli/                     # CLI package (published to PyPI)
│   ├── pyproject.toml
│   ├── rgrid/
│   │   ├── __init__.py
│   │   ├── cli.py           # Click commands
│   │   ├── client.py        # API client
│   │   ├── config.py        # Credentials handling
│   │   └── upload.py        # File upload logic
│   └── tests/
├── api/                     # FastAPI control plane
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py          # FastAPI app initialization
│   │   ├── api/             # Route handlers (THIN)
│   │   │   └── v1/
│   │   │       ├── __init__.py  # Auto-register routers
│   │   │       ├── executions.py
│   │   │       ├── artifacts.py
│   │   │       ├── api_keys.py
│   │   │       ├── accounts.py
│   │   │       └── health.py
│   │   ├── core/
│   │   │   ├── config.py    # Settings (Pydantic BaseSettings)
│   │   │   ├── security.py  # Auth helpers
│   │   │   └── errors.py    # Error models
│   │   ├── db/
│   │   │   ├── base.py      # Import all models
│   │   │   ├── session.py   # Async session factory
│   │   │   └── models/      # SQLAlchemy models (explicit types)
│   │   │       ├── account.py
│   │   │       ├── user.py
│   │   │       ├── execution.py
│   │   │       ├── worker.py
│   │   │       ├── artifact.py
│   │   │       └── server_type.py
│   │   ├── services/        # Business logic (PURE FUNCTIONS)
│   │   │   ├── execution_service.py
│   │   │   ├── artifact_service.py
│   │   │   ├── worker_service.py
│   │   │   ├── cache_service.py
│   │   │   └── billing_service.py
│   │   ├── schemas/         # Pydantic request/response models
│   │   │   ├── execution.py
│   │   │   ├── artifact.py
│   │   │   ├── account.py
│   │   │   └── error.py
│   │   └── deps.py          # FastAPI dependencies
│   ├── Dockerfile
│   └── tests/
│       ├── conftest.py      # Pytest fixtures
│       ├── test_executions.py
│       └── test_billing.py
├── orchestrator/            # Worker provisioning & lifecycle
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── provisioner.py   # Hetzner API integration
│   │   ├── scaler.py        # Auto-scaling logic
│   │   └── lifecycle.py     # Worker TTL management
│   ├── Dockerfile
│   └── tests/
├── runner/                  # Worker agent (runs on Hetzner nodes)
│   ├── runner/
│   │   ├── __init__.py
│   │   ├── agent.py         # Ray worker agent
│   │   ├── executor.py      # Docker execution
│   │   └── io_handler.py    # MinIO upload/download
│   ├── Dockerfile
│   └── tests/
├── website/                 # Marketing website (Next.js) → rgrid.dev
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx       # Root layout (no auth)
│   │   ├── page.tsx         # Landing page
│   │   ├── features/
│   │   │   └── page.tsx     # Features page
│   │   ├── pricing/
│   │   │   └── page.tsx     # Pricing page
│   │   ├── docs/
│   │   │   └── page.tsx     # Docs landing
│   │   └── blog/
│   │       └── page.tsx     # Blog (optional for MVP)
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Hero.tsx
│   │   └── CTAButton.tsx
│   └── public/
│       ├── logo.svg
│       └── images/
├── console/                 # Authenticated dashboard (Next.js) → app.rgrid.dev
│   ├── package.json
│   ├── next.config.js
│   ├── middleware.ts        # Clerk auth middleware
│   ├── app/
│   │   ├── layout.tsx       # Clerk wrapper + nav
│   │   ├── page.tsx         # Dashboard home
│   │   ├── jobs/
│   │   │   ├── page.tsx     # Jobs list
│   │   │   └── [id]/
│   │   │       └── page.tsx # Job details
│   │   ├── executions/
│   │   │   ├── page.tsx     # Executions list
│   │   │   └── [id]/
│   │   │       └── page.tsx # Execution details (logs, artifacts)
│   │   ├── settings/
│   │   │   ├── page.tsx     # Account settings
│   │   │   ├── api-keys/
│   │   │   │   └── page.tsx # API key management
│   │   │   └── billing/
│   │   │       └── page.tsx # Credits, payments
│   │   └── api/             # Next.js API routes (if needed)
│   ├── components/
│   │   ├── JobsList.tsx
│   │   ├── ExecutionLogs.tsx
│   │   ├── CreditBalance.tsx
│   │   └── Navbar.tsx
│   └── lib/
│       ├── api-client.ts    # FastAPI client
│       └── clerk.ts         # Clerk config
├── infra/                   # Infrastructure as code
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── nginx.conf           # Routes rgrid.dev, app.rgrid.dev, api.rgrid.dev
│   ├── cloud-init.yml       # Worker bootstrap script
│   └── terraform/           # Future: IaC for multi-cloud
├── docs/                    # Documentation
│   ├── architecture.md      # This document
│   ├── PRD.md
│   └── TABLE_OF_CONTENTS.md
└── tests/                   # Integration tests
    └── test_e2e.py
```

**Packaging Strategy:**
- `rgrid-cli` → PyPI (users install via `pip install rgrid-cli`)
- `api`, `orchestrator`, `runner` → Docker images (not published)
- `website`, `console` → Next.js apps (hosted on control plane, not packaged)
- `rgrid_common` → Internal (imported by other packages, not published)

---

### Decision 2: Database Schema Design ✅

**Decision:** PostgreSQL with MICRONS for cost tracking, multi-tenant account model, shared worker pool.

**Key Insights from mediaconvert.io:**
1. Use **BIGINT** for all cost fields (store microns, not decimals)
2. Workers are **shared pool** (not scoped to accounts)
3. Track billing hours on workers to maximize utilization
4. Separate estimated cost (immediate) from finalized cost (amortized)

**Complete Schema:** See [Database Schema](#database-schema) section below.

**Critical Tables:**
- `accounts` - Multi-tenant billing entities
- `users` - Individuals (many-to-many with accounts)
- `server_types` - Data-driven worker types synced from Hetzner API
- `workers` - Shared worker pool (NOT scoped to accounts)
- `executions` - Jobs (belong to accounts, run on shared workers)
- `account_credits` - Financial ledger (all in microns)
- `cache_entries` - Content-hash caching for scripts/dependencies

**Money Handling:**
```python
# rgrid_common/money.py
class Money:
    """
    All costs stored as BIGINT microns in database.
    1 EUR/USD = 1,000,000 microns
    1 cent = 10,000 microns
    """
    MICROS_PER_UNIT = 1_000_000

    def __init__(self, micros: int, currency: str = 'EUR'):
        self.micros = int(micros)  # Always integer!
        self.currency = currency.upper()

    def to_units(self) -> float:
        return self.micros / self.MICROS_PER_UNIT

    def format(self) -> str:
        units = self.to_units()
        symbol = '€' if self.currency == 'EUR' else '$'
        return f"{symbol}{units:.6f}".rstrip('0').rstrip('.')
```

---

### Decision 3: Ray Cluster Architecture ✅

**Decision:** Separate Ray head node container on control plane, workers join via hardcoded IP, object store on head node.

**Architecture:**

```
Control Plane (Hetzner CX31):
├── FastAPI Container
│   └── Connects to: ray://ray-head:10001
├── Ray Head Node Container
│   ├── Scheduler + Object Store
│   ├── Dashboard: :8265
│   └── Client port: :10001
├── PostgreSQL
├── MinIO
└── Docker Registry

Workers (Hetzner CX22):
└── Ray Worker Container
    ├── Joins via: ray start --address=10.0.0.1:6379
    ├── num-cpus=2, memory=4GB
    └── Executes Docker containers for user scripts
```

**Worker Provisioning:**

```python
# orchestrator/provisioner.py
def provision_worker(server_type: ServerType) -> Worker:
    """Provision a new Hetzner worker and join Ray cluster."""

    ray_head_ip = os.getenv("CONTROL_PLANE_PRIVATE_IP")  # 10.0.0.1

    cloud_init = f"""
    #cloud-config
    packages:
      - docker.io
    runcmd:
      - docker run -d --name ray-worker --network=host \\
          rayproject/ray:latest \\
          ray start \\
            --address={ray_head_ip}:6379 \\
            --num-cpus={server_type.cpu_cores} \\
            --memory={server_type.memory_mb * 1024 * 1024} \\
            --block
    """

    server = hetzner_client.servers.create(
        name=f"rgrid-worker-{uuid.uuid4().hex[:8]}",
        server_type=server_type.server_type,  # "cx22"
        image="ubuntu-22.04",
        user_data=cloud_init,
        location="nbg1"
    )

    # Record worker in database
    worker = Worker(
        hetzner_server_id=server.id,
        worker_id=server.name,
        server_type_id=server_type.id,
        max_concurrent_jobs=server_type.max_concurrent_jobs,
        ip_address=server.private_net[0].ip,
        billing_hour_started_at=datetime.utcnow(),
        billing_hour_ends_at=datetime.utcnow() + timedelta(hours=1),
        status="provisioning"
    )

    return worker
```

**Task Submission:**

```python
# api/app/services/execution_service.py
import ray

@ray.remote(num_cpus=1, memory=2*1024*1024*1024)  # 2GB
def execute_job(execution_id: str, script_hash: str, runtime: str, args: list):
    """
    This function runs on worker nodes.
    Workers can run multiple in parallel based on available CPU.
    """
    from runner.executor import DockerExecutor

    executor = DockerExecutor()
    result = executor.run(
        execution_id=execution_id,
        script_hash=script_hash,
        runtime=runtime,
        args=args
    )
    return result

# Submit to Ray (non-blocking)
result_ref = execute_job.remote(
    execution_id=str(execution.id),
    script_hash=execution.script_hash,
    runtime=execution.runtime,
    args=execution.command
)
```

**Rationale:**
- **Separate container:** API can restart without killing Ray cluster
- **Hardcoded IP:** Simpler than DNS, works with Hetzner private networking
- **Head node object store:** Sufficient for MVP, can externalize to Redis later

---

### Decision 4: Docker Image Management ✅

**Decision:** MinIO-backed local registry on control plane, build images on control plane, multi-stage Dockerfiles with hash-based layer caching.

**Registry Setup:**

```yaml
# infra/docker-compose.yml
services:
  registry:
    image: registry:2
    environment:
      REGISTRY_STORAGE: s3
      REGISTRY_STORAGE_S3_ENDPOINT: minio:9000
      REGISTRY_STORAGE_S3_BUCKET: docker-images
      REGISTRY_STORAGE_S3_ACCESSKEY: ${MINIO_ROOT_USER}
      REGISTRY_STORAGE_S3_SECRETKEY: ${MINIO_ROOT_PASSWORD}
    ports:
      - "5000:5000"
```

**Image Build Strategy:**

```python
# api/app/services/cache_service.py
def build_script_image(script_hash: str, requirements_hash: str, runtime: str):
    """
    Build Docker image with multi-stage caching.

    Level 1 Cache: Dependencies layer (by requirements_hash)
    Level 2 Cache: Script layer (by script_hash)
    """

    # Generate multi-stage Dockerfile
    dockerfile = f"""
    # Stage 1: Dependencies (cached by requirements_hash)
    FROM {runtime} as deps
    COPY requirements_{requirements_hash}.txt /tmp/requirements.txt
    RUN pip install --no-cache-dir -r /tmp/requirements.txt

    # Stage 2: Script (cached by script_hash)
    FROM deps
    COPY script_{script_hash}.py /app/script.py
    WORKDIR /app
    CMD ["python", "script.py"]
    """

    # Build image
    client = docker.from_env()
    image, logs = client.images.build(
        fileobj=io.BytesIO(dockerfile.encode()),
        tag=f"localhost:5000/script-{script_hash}:latest",
        rm=True
    )

    # Push to local registry
    client.images.push(f"localhost:5000/script-{script_hash}:latest")

    # Record in cache_entries
    cache_entry = CacheEntry(
        cache_type="script",
        content_hash=script_hash,
        docker_image_tag=f"localhost:5000/script-{script_hash}:latest",
        runtime=runtime
    )

    return cache_entry
```

**Cache Hit Flow:**

```
1. User submits script.py (hash: abc123)
2. Check cache: SELECT * FROM cache_entries WHERE content_hash='abc123' AND cache_type='script'
3. If found: Worker pulls localhost:5000/script-abc123:latest (instant)
4. If NOT found: Build image (30-60s), save to registry, insert into cache
5. Next execution with same script = instant pull
```

**MinIO Bucket Structure:**

```
minio://
├── scripts/{script_hash}/script.py
├── dependencies/{requirements_hash}/requirements.txt
├── inputs/{execution_id}/*.csv
├── outputs/{execution_id}/*.json
├── logs/{execution_id}/execution.log
└── docker-images/  (registry backend)
```

---

### Decision 5: File Upload/Download Flow ✅

**Decision:** Hybrid approach - small files (<10MB) via API, large files (>10MB) via presigned URLs, parallel uploads for batches.

**Upload Flow:**

```python
# CLI smart upload
def upload_file(file_path: Path, api_client: ApiClient):
    """Upload file with size-based strategy."""

    file_size = file_path.stat().st_size

    if file_size < 10 * 1024 * 1024:  # <10MB
        # Upload via API (simple, can validate)
        with open(file_path, 'rb') as f:
            response = api_client.post(
                "/v1/artifacts/upload",
                files={'file': f}
            )
        return response['object_key']

    else:
        # Upload directly to MinIO (fast, no API bottleneck)
        # 1. Request presigned URL
        response = api_client.post(
            "/v1/artifacts/upload-url",
            json={
                "filename": file_path.name,
                "file_size": file_size,
                "type": "script"
            }
        )

        # 2. Upload directly to MinIO
        with open(file_path, 'rb') as f:
            requests.put(response['upload_url'], data=f)

        return response['object_key']
```

**Batch Upload (Parallel):**

```python
import asyncio
from tqdm import tqdm

async def upload_files_parallel(files: List[Path], max_concurrent=10):
    """Upload multiple files in parallel with progress bar."""

    semaphore = asyncio.Semaphore(max_concurrent)

    async def upload_one(file_path: Path):
        async with semaphore:
            return await upload_file(file_path)

    # Progress bar
    with tqdm(total=len(files), unit='file') as pbar:
        tasks = []
        for file in files:
            task = upload_one(file)
            task.add_done_callback(lambda _: pbar.update(1))
            tasks.append(task)

        return await asyncio.gather(*tasks)
```

**Download Flow:**

```python
# API returns presigned download URLs
@router.get("/v1/executions/{execution_id}/artifacts")
async def list_artifacts(execution_id: UUID):
    """List execution outputs with download URLs."""

    objects = minio_client.list_objects(
        bucket_name="outputs",
        prefix=f"{execution_id}/"
    )

    return {
        "artifacts": [
            {
                "filename": obj.object_name.split('/')[-1],
                "size": obj.size,
                "download_url": minio_client.presigned_get_object(
                    bucket_name="outputs",
                    object_name=obj.object_name,
                    expires=timedelta(hours=1)
                )
            }
            for obj in objects
        ]
    }

# CLI downloads directly from MinIO
def download_outputs(execution_id: str):
    """Download all outputs for an execution."""

    artifacts = api_client.get(f"/v1/executions/{execution_id}/artifacts")

    output_dir = Path("./outputs") / execution_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        # Download directly from presigned URL
        response = requests.get(artifact['download_url'], stream=True)

        output_path = output_dir / artifact['filename']
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Downloaded: {artifact['filename']}")
```

**Retention Policy:**
- Scripts/dependencies: Keep forever (cached)
- Inputs/outputs: 30 days default (configurable per account)
- Logs: 7 days default

---

### Decision 6: Authentication Flow ✅

**Decision:** Dual authentication - Clerk (web console) + API Keys (CLI), following AWS credential pattern.

**API Key Generation:**

```python
# Web console (Clerk authenticated)
@router.post("/v1/api-keys")
async def create_api_key(
    name: str,
    user: User = Depends(get_current_user_from_clerk)
):
    """Generate new API key for account."""

    # Generate secure random key
    raw_key = secrets.token_urlsafe(32)

    # Hash for storage (bcrypt)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt())

    # Store in database
    api_key = ApiKey(
        account_id=user.default_account_id,
        name=name,
        key_hash=key_hash
    )
    db.add(api_key)
    await db.commit()

    # Return raw key ONCE (never shown again!)
    return {
        "id": api_key.id,
        "name": name,
        "api_key": f"rgrid_sk_{raw_key}",
        "message": "Save this key - it won't be shown again!"
    }
```

**API Key Verification:**

```python
# API endpoint authentication
async def verify_api_key(api_key: str) -> Account:
    """Verify API key and return account."""

    if not api_key.startswith("rgrid_sk_"):
        raise AuthenticationError("Invalid API key format")

    raw_key = api_key.replace("rgrid_sk_", "")

    # Find all active keys (can't query by hash)
    api_keys = await db.query(ApiKey).filter_by(is_active=True).all()

    # Check each key (bcrypt compare)
    for key in api_keys:
        if bcrypt.checkpw(raw_key.encode(), key.key_hash):
            # Update last used
            key.last_used_at = datetime.utcnow()
            await db.commit()

            return await db.query(Account).get(key.account_id)

    raise AuthenticationError("Invalid API key")

# FastAPI dependency
async def get_authenticated_account(
    api_key: str = Header(None, alias="X-API-Key"),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Account:
    """Dual authentication: API key (CLI) or Clerk token (web)."""

    # Try API key first (CLI)
    if api_key:
        return await verify_api_key(api_key)

    # Try Clerk token (web)
    if credentials:
        user = await verify_clerk_token(credentials.credentials)
        return user.default_account

    raise HTTPException(status_code=401, detail="Authentication required")
```

**CLI Credentials Storage:**

```ini
# ~/.rgrid/credentials (permissions: 0600)
[default]
api_key = rgrid_sk_abc123def456...
api_url = https://api.rgrid.dev

[staging]
api_key = rgrid_sk_staging789...
api_url = https://staging.rgrid.dev
```

```python
# cli/rgrid/config.py
def load_credentials(profile: str = "default") -> dict:
    """Load credentials from ~/.rgrid/credentials."""

    creds_path = Path.home() / ".rgrid" / "credentials"

    if not creds_path.exists():
        raise CredentialsNotFoundError(
            "No credentials found. Run: rgrid init"
        )

    config = configparser.ConfigParser()
    config.read(creds_path)

    return {
        "api_key": config[profile]["api_key"],
        "api_url": config[profile].get("api_url", "https://api.rgrid.dev")
    }
```

---

### Decision 7: API Route Structure ✅

**Decision:** LLM-agent-friendly FastAPI structure with explicit types, pure service functions, comprehensive OpenAPI docs.

**Route Organization:**

```
Base: https://api.rgrid.dev/v1

POST   /v1/executions              # Create execution
GET    /v1/executions              # List executions (filtered, paginated)
GET    /v1/executions/{id}         # Get execution
POST   /v1/executions/{id}/cancel  # Cancel execution
POST   /v1/executions/{id}/retry   # Retry failed execution

GET    /v1/executions/{id}/logs    # Get logs (paginated)
WS     /v1/executions/{id}/logs/stream  # Stream logs (WebSocket)

POST   /v1/artifacts/upload-url    # Get presigned upload URL
POST   /v1/artifacts/upload        # Upload small file via API
GET    /v1/executions/{id}/artifacts  # List outputs with download URLs

POST   /v1/api-keys                # Create API key
GET    /v1/api-keys                # List API keys
DELETE /v1/api-keys/{id}           # Revoke API key

GET    /v1/account                 # Get account details
GET    /v1/account/usage           # Get usage statistics
POST   /v1/account/credits         # Add credits (Stripe)
GET    /v1/account/costs           # Get cost breakdown

GET    /v1/health                  # Health check
GET    /v1/status/workers          # Worker pool status
```

**LLM-Friendly Route Example:**

```python
# api/app/api/v1/executions.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.execution import ExecutionCreate, Execution, ExecutionList
from app.schemas.error import ErrorResponse
from app.services import execution_service
from app.deps import get_authenticated_account

router = APIRouter(prefix="/executions", tags=["executions"])

@router.post(
    "",
    response_model=Execution,
    status_code=201,
    summary="Create a new execution",
    description="""
    Submit a Python script for remote execution.

    **Process:**
    1. Script is uploaded to MinIO storage
    2. Content hash is calculated for caching
    3. Execution is queued for processing
    4. Returns immediately with execution ID

    **Authentication:** Requires API key (X-API-Key header)
    **Cost:** Execution costs are deducted from account credits
    """,
    responses={
        201: {"description": "Execution created successfully"},
        402: {"model": ErrorResponse, "description": "Insufficient credits"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    }
)
async def create_execution(
    execution_data: ExecutionCreate,
    account: Account = Depends(get_authenticated_account)
):
    """
    Create a new execution.

    This is a THIN route handler - all logic in service layer.

    Args:
        execution_data: Validated execution parameters
        account: Authenticated account from API key

    Returns:
        Created execution with ID and status
    """
    try:
        return await execution_service.create(db, account, execution_data)
    except ValueError as e:
        if "Insufficient credits" in str(e):
            raise HTTPException(
                status_code=402,
                detail=ErrorResponse(
                    code="INSUFFICIENT_CREDITS",
                    message=str(e),
                    details={
                        "current_balance_microns": account.credit_balance_microns,
                        "currency": account.preferred_currency
                    }
                ).dict()
            )
        raise
```

**Pure Service Function:**

```python
# api/app/services/execution_service.py
async def create(
    db: AsyncSession,
    account: Account,
    execution_data: ExecutionCreate
) -> Execution:
    """
    Create a new execution.

    PURE FUNCTION - no HTTP concerns, only business logic.

    Args:
        db: Database session
        account: Account creating execution
        execution_data: Validated execution parameters

    Returns:
        Created execution

    Raises:
        ValueError: If account has insufficient credits
    """
    # Calculate script hash
    script_hash = hashlib.sha256(
        execution_data.script_content.encode()
    ).hexdigest()

    # Check credit balance
    required_cost = await estimate_cost(db, execution_data)
    if account.credit_balance_microns < required_cost:
        raise ValueError(
            f"Insufficient credits. Required: {Money.from_micros(required_cost).format()}, "
            f"Available: {Money.from_micros(account.credit_balance_microns).format()}"
        )

    # Upload script to MinIO
    script_key = await artifact_service.upload_script(
        script_hash,
        execution_data.script_content
    )

    # Create execution record
    execution = ExecutionModel(
        account_id=account.id,
        script_hash=script_hash,
        script_path=script_key,
        runtime=execution_data.runtime,
        status="pending",
        estimated_cost_microns=required_cost
    )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Submit to Ray cluster (async, non-blocking)
    await submit_to_ray(execution.id, script_hash, execution_data.runtime)

    return Execution.from_orm(execution)
```

---

### Decision 8: WebSocket Implementation

**Decision:** WebSocket streaming for real-time log feedback, with polling fallback.

**WebSocket Server:**

```python
# api/app/api/v1/executions.py
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@router.websocket("/{execution_id}/logs/stream")
async def stream_logs(
    websocket: WebSocket,
    execution_id: UUID
):
    """
    Stream execution logs in real-time via WebSocket.

    Message format:
    {
        "line": 42,
        "stream": "stdout",
        "timestamp": "2025-11-15T01:00:05Z",
        "content": "Processing file 1/100..."
    }
    """
    await websocket.accept()

    try:
        # Verify execution belongs to account (from query params or initial message)
        # ... authentication logic ...

        last_line = 0

        while True:
            # Fetch new logs from database
            new_logs = await db.execute(
                select(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .where(ExecutionLog.line_number > last_line)
                .order_by(ExecutionLog.line_number.asc())
                .limit(100)
            )

            logs = new_logs.scalars().all()

            for log in logs:
                await websocket.send_json({
                    "line": log.line_number,
                    "stream": log.stream,
                    "timestamp": log.timestamp.isoformat(),
                    "content": log.content
                })
                last_line = log.line_number

            # Check if execution is complete
            execution = await db.get(ExecutionModel, execution_id)
            if execution.status in ['completed', 'failed', 'cancelled']:
                await websocket.send_json({
                    "type": "status",
                    "status": execution.status,
                    "message": f"Execution {execution.status}"
                })
                break

            # Wait before checking for more logs
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        # Client disconnected - execution continues
        pass
```

**CLI WebSocket Client:**

```python
# cli/rgrid/client.py
import asyncio
import websockets

async def stream_logs(execution_id: str, api_url: str, api_key: str):
    """Connect to WebSocket and stream logs to console."""

    ws_url = f"wss://{api_url.replace('https://', '')}/v1/executions/{execution_id}/logs/stream"

    async with websockets.connect(
        ws_url,
        extra_headers={"X-API-Key": api_key}
    ) as websocket:

        print(f"Streaming logs for execution {execution_id}...")

        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "status":
                print(f"\n✓ Execution {data['status']}")
                break

            # Format log line
            timestamp = data['timestamp']
            stream = data['stream']
            content = data['content']

            # Color code: stdout=white, stderr=red
            color = "\033[91m" if stream == "stderr" else ""
            reset = "\033[0m" if stream == "stderr" else ""

            print(f"{color}[{timestamp}] {content}{reset}")

# Usage
@click.command()
@click.argument('script')
@click.option('--watch', is_flag=True, help="Stream logs in real-time")
def run(script, watch):
    """Run script remotely."""

    # Submit execution
    execution = api_client.create_execution(script)
    print(f"Execution started: {execution['id']}")

    if watch:
        # Stream logs via WebSocket
        asyncio.run(stream_logs(execution['id'], api_url, api_key))
    else:
        print(f"View logs: rgrid logs {execution['id']} --follow")
```

**Polling Fallback:**

```python
# If WebSocket unavailable, fall back to polling
async def poll_logs(execution_id: str):
    """Poll for logs when WebSocket unavailable."""

    last_line = 0

    while True:
        # Get new logs
        response = api_client.get(
            f"/v1/executions/{execution_id}/logs",
            params={"offset": last_line, "limit": 100}
        )

        for log in response['logs']:
            print(f"[{log['timestamp']}] {log['content']}")
            last_line = log['line']

        # Check if complete
        execution = api_client.get(f"/v1/executions/{execution_id}")
        if execution['status'] in ['completed', 'failed', 'cancelled']:
            break

        # Wait before next poll
        await asyncio.sleep(2)
```

**Log Storage (Worker → Database):**

```python
# runner/executor.py
async def capture_logs(execution_id: UUID, container):
    """Capture Docker container logs and stream to database."""

    for log in container.logs(stream=True, follow=True):
        line_number = ...  # Increment counter

        await db.execute(
            insert(ExecutionLog).values(
                execution_id=execution_id,
                line_number=line_number,
                stream="stdout",  # or "stderr"
                content=log.decode('utf-8').strip(),
                timestamp=datetime.utcnow()
            )
        )
        await db.commit()
```

---

### Decision 9: Worker Provisioning Logic

**Decision:** Smart queue-based provisioning that maximizes worker utilization within billing hours.

**Provisioning Strategy:**

```python
# orchestrator/scaler.py
async def should_provision_worker() -> tuple[bool, str]:
    """
    Decide if we should provision a new worker.

    Returns:
        (should_provision, reason)
    """
    # Get queue state
    queue_state = await get_queue_state()

    pending = queue_state.pending_jobs
    available_slots = queue_state.available_slots
    active_workers = queue_state.active_workers

    # Rule 1: If we have available slots, don't provision
    if available_slots > 0:
        return (False, f"Available slots: {available_slots}")

    # Rule 2: If no pending jobs, don't provision
    if pending == 0:
        return (False, "No pending jobs")

    # Rule 3: Calculate how many jobs will complete soon
    running_jobs = queue_state.running_jobs
    avg_duration = queue_state.avg_job_duration_seconds or 300

    jobs_completing_in_5min = estimate_jobs_completing_in(
        running_jobs, avg_duration, seconds=300
    )

    # If pending jobs will fit in soon-to-be-available slots, wait
    if pending <= jobs_completing_in_5min:
        return (False, f"{pending} jobs will fit in {jobs_completing_in_5min} slots freeing up")

    # Rule 4: Calculate queue processing time
    if active_workers == 0:
        # No workers at all - provision immediately
        return (True, "No active workers")

    estimated_queue_time = (pending * avg_duration) / (active_workers * 2)  # 2 slots per CX22

    # Only provision if queue time > threshold (10 minutes)
    if estimated_queue_time > 600:
        return (True, f"Queue time {estimated_queue_time}s > 600s threshold")

    return (False, f"Queue time {estimated_queue_time}s within threshold")


async def should_terminate_worker(worker: Worker) -> tuple[bool, str]:
    """
    Decide if worker should be terminated.

    CRITICAL: Maximize billing hour utilization!
    """
    now = datetime.utcnow()

    # Rule 1: Never terminate if within billing hour
    if worker.billing_hour_ends_at > now:
        return (False, f"Within billing hour (ends {worker.billing_hour_ends_at})")

    # Rule 2: Never terminate if running jobs
    if worker.current_concurrent_jobs > 0:
        return (False, f"Running {worker.current_concurrent_jobs} jobs")

    # Rule 3: Check if pending jobs could use this worker
    pending_jobs = await db.execute(
        select(func.count())
        .select_from(Execution)
        .where(Execution.status == 'pending')
    )

    pending_count = pending_jobs.scalar()

    if pending_count > 0:
        return (False, f"{pending_count} pending jobs - keep worker available")

    # Rule 4: Billing hour expired + idle + no pending jobs = terminate
    return (True, "Billing hour expired, idle, no pending jobs")


async def autoscaler_loop():
    """Main autoscaler loop - runs every 30 seconds."""

    while True:
        try:
            # Check if we should provision
            should_provision, reason = await should_provision_worker()

            if should_provision:
                logger.info(f"Provisioning worker: {reason}")

                # Select optimal server type
                server_type = await select_optimal_server_type()

                # Provision worker
                worker = await provision_worker(server_type)

                # Record metrics
                await record_queue_metrics(
                    should_scale_up=True,
                    recommended_worker_count=await get_active_worker_count() + 1,
                    decision_reason=reason
                )

            # Check workers for termination
            workers = await db.execute(
                select(Worker)
                .where(Worker.status.in_(['active', 'idle']))
            )

            for worker in workers.scalars():
                should_terminate, reason = await should_terminate_worker(worker)

                if should_terminate:
                    logger.info(f"Terminating worker {worker.worker_id}: {reason}")
                    await terminate_worker(worker)

        except Exception as e:
            logger.error(f"Autoscaler error: {e}")

        # Run every 30 seconds
        await asyncio.sleep(30)
```

**Worker Lifecycle:**

```
1. PROVISIONING (0-60s)
   - Hetzner creates server
   - Cloud-init installs Docker
   - Ray worker joins cluster

2. ACTIVE (60-3600s)
   - Available for job assignment
   - billing_hour_started_at = provision time
   - billing_hour_ends_at = +60 minutes

3. DRAINING (when idle after billing hour)
   - No new jobs assigned
   - Wait for running jobs to complete

4. TERMINATING
   - All jobs complete
   - Hetzner destroys server

5. TERMINATED
   - Server destroyed
   - Worker record kept for audit/cost tracking
```

**Cost Finalization (After Billing Hour):**

```python
# Background job runs every hour
async def finalize_worker_costs():
    """
    Finalize execution costs after billing hour ends.

    Amortize worker cost across all jobs that ran during the hour.
    """
    # Find workers whose billing hour ended in last hour
    workers = await db.execute(
        select(Worker)
        .where(Worker.billing_hour_ends_at.between(
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow()
        ))
        .where(Worker.status == 'terminated')
    )

    for worker in workers.scalars():
        # Get all executions that ran on this worker during billing hour
        executions = await db.execute(
            select(Execution)
            .where(Execution.worker_id == worker.id)
            .where(Execution.started_at >= worker.billing_hour_started_at)
            .where(Execution.started_at < worker.billing_hour_ends_at)
        )

        execution_list = executions.scalars().all()
        total_jobs = len(execution_list)

        if total_jobs == 0:
            continue

        # Amortize worker cost across all jobs
        server_type = await db.get(ServerType, worker.server_type_id)
        hourly_cost = server_type.hourly_cost_microns
        cost_per_job = hourly_cost // total_jobs

        # Update each execution with finalized cost
        for execution in execution_list:
            execution.final_cost_microns = cost_per_job
            execution.cost_finalized_at = datetime.utcnow()

        await db.commit()

        logger.info(
            f"Finalized costs for worker {worker.worker_id}: "
            f"{total_jobs} jobs, {cost_per_job} microns each"
        )
```

---

### Decision 10: Content-Hash Caching

**Decision:** Three-level caching with sha256 hashes, tracked in cache_entries table.

**Caching Levels:**

```python
# Level 1: Script Content Cache
def get_or_build_script_image(script_content: str, runtime: str) -> str:
    """
    Get cached script image or build new one.

    Returns: Docker image tag
    """
    script_hash = hashlib.sha256(script_content.encode()).hexdigest()

    # Check cache
    cache_entry = await db.execute(
        select(CacheEntry)
        .where(CacheEntry.cache_type == 'script')
        .where(CacheEntry.content_hash == script_hash)
    )

    cached = cache_entry.scalar_one_or_none()

    if cached:
        # Cache hit - update access time
        cached.last_accessed_at = datetime.utcnow()
        cached.access_count += 1
        await db.commit()

        logger.info(f"Cache HIT: script {script_hash[:8]}")
        return cached.docker_image_tag

    # Cache miss - build image
    logger.info(f"Cache MISS: script {script_hash[:8]} - building...")

    # Upload script to MinIO
    script_key = f"scripts/{script_hash}/script.py"
    await minio_upload(script_key, script_content)

    # Check requirements.txt cache (Level 2)
    requirements = extract_requirements(script_content)
    requirements_hash = hashlib.sha256(requirements.encode()).hexdigest()

    # Build image with multi-stage caching
    image_tag = await build_script_image(
        script_hash,
        requirements_hash,
        runtime
    )

    # Save to cache
    cache_entry = CacheEntry(
        cache_type='script',
        content_hash=script_hash,
        docker_image_tag=image_tag,
        runtime=runtime,
        minio_bucket='scripts',
        minio_key=script_key
    )
    db.add(cache_entry)
    await db.commit()

    return image_tag


# Level 2: Dependency Cache (Docker layer)
def build_script_image(script_hash: str, requirements_hash: str, runtime: str):
    """
    Build with multi-stage Docker for dependency layer caching.
    """
    dockerfile = f"""
    # Stage 1: Dependencies (CACHED by requirements_hash)
    FROM {runtime} as deps
    COPY requirements_{requirements_hash}.txt /tmp/requirements.txt
    RUN pip install --no-cache-dir -r /tmp/requirements.txt

    # Stage 2: Script (CACHED by script_hash)
    FROM deps
    COPY script_{script_hash}.py /app/script.py
    WORKDIR /app
    CMD ["python", "script.py"]
    """

    # Docker automatically caches each layer
    # - If requirements_hash unchanged → Stage 1 cached
    # - If script_hash unchanged → Stage 2 cached

    image, logs = docker_client.images.build(
        fileobj=io.BytesIO(dockerfile.encode()),
        tag=f"localhost:5000/script-{script_hash}:latest"
    )

    docker_client.images.push(f"localhost:5000/script-{script_hash}:latest")

    return f"localhost:5000/script-{script_hash}:latest"


# Level 3: Input File Cache (Optional - for repeated batch jobs)
def get_cached_input(input_hash: str) -> Optional[str]:
    """
    Check if input file was previously uploaded.

    Use case: User runs same batch job multiple times.
    """
    cache_entry = await db.execute(
        select(CacheEntry)
        .where(CacheEntry.cache_type == 'input')
        .where(CacheEntry.content_hash == input_hash)
    )

    cached = cache_entry.scalar_one_or_none()

    if cached:
        return cached.minio_key

    return None
```

**Cache Performance:**

```
Cold Start (First Execution):
- Script upload: 2s
- Image build: 60-90s (full pip install)
- Total: ~90s

Warm Start (Script Cached):
- Script hash lookup: 10ms
- Image pull from registry: 3-5s
- Total: ~5s

Hot Start (Worker has image):
- Container start: <1s
- Total: <1s
```

**Cache Eviction:**

```python
# Background job runs daily
async def evict_stale_cache():
    """Remove cache entries not accessed in 90 days."""

    cutoff = datetime.utcnow() - timedelta(days=90)

    stale_entries = await db.execute(
        select(CacheEntry)
        .where(CacheEntry.last_accessed_at < cutoff)
    )

    for entry in stale_entries.scalars():
        # Delete from MinIO
        if entry.minio_key:
            await minio_client.remove_object(
                entry.minio_bucket,
                entry.minio_key
            )

        # Delete from registry
        if entry.docker_image_tag:
            await delete_registry_image(entry.docker_image_tag)

        # Delete from database
        await db.delete(entry)

    await db.commit()
```

---

### Decision 11: Error Handling Strategy

**Decision:** Consistent error codes, structured ErrorResponse model, service-layer exceptions mapped to HTTP status codes.

**Error Response Model:**

```python
# api/app/schemas/error.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ErrorResponse(BaseModel):
    """
    Standard error response for all API errors.

    LLM agents can understand and handle errors consistently.
    """
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context"
    )

    class Config:
        schema_extra = {
            "example": {
                "code": "INSUFFICIENT_CREDITS",
                "message": "Account has insufficient credits. Balance: €2.50, Required: €5.00",
                "details": {
                    "current_balance_microns": 2500000,
                    "required_microns": 5000000,
                    "currency": "EUR"
                }
            }
        }
```

**Standard Error Codes:**

```python
# api/app/core/errors.py
class ErrorCode:
    """Standard error codes across API."""

    # Authentication (401)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_API_KEY = "INVALID_API_KEY"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Authorization (403)
    FORBIDDEN = "FORBIDDEN"

    # Payment Required (402)
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"

    # Not Found (404)
    EXECUTION_NOT_FOUND = "EXECUTION_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"

    # Validation (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SCRIPT = "INVALID_SCRIPT"
    INVALID_RUNTIME = "INVALID_RUNTIME"

    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"
    STORAGE_ERROR = "STORAGE_ERROR"


class RGridException(Exception):
    """Base exception for RGrid errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict] = None,
        status_code: int = 500
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

class InsufficientCreditsError(RGridException):
    def __init__(self, current: int, required: int, currency: str = "EUR"):
        super().__init__(
            code=ErrorCode.INSUFFICIENT_CREDITS,
            message=f"Insufficient credits. Balance: {Money.from_micros(current, currency).format()}, Required: {Money.from_micros(required, currency).format()}",
            details={
                "current_balance_microns": current,
                "required_microns": required,
                "currency": currency
            },
            status_code=402
        )

class ExecutionNotFoundError(RGridException):
    def __init__(self, execution_id: UUID):
        super().__init__(
            code=ErrorCode.EXECUTION_NOT_FOUND,
            message=f"Execution {execution_id} not found or not authorized",
            details={"execution_id": str(execution_id)},
            status_code=404
        )
```

**Exception Handler:**

```python
# api/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RGridException)
async def rgrid_exception_handler(request: Request, exc: RGridException):
    """Handle all RGrid exceptions with consistent format."""

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""

    logger.exception(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__}
            }
        }
    )
```

**Service Layer Error Handling:**

```python
# api/app/services/execution_service.py
async def create(db: AsyncSession, account: Account, data: ExecutionCreate):
    """
    Create execution - raises domain exceptions.
    """
    # Validate credit balance
    required_cost = await estimate_cost(db, data)

    if account.credit_balance_microns < required_cost:
        raise InsufficientCreditsError(
            current=account.credit_balance_microns,
            required=required_cost,
            currency=account.preferred_currency
        )

    # Validate runtime
    if not is_valid_runtime(data.runtime):
        raise RGridException(
            code=ErrorCode.INVALID_RUNTIME,
            message=f"Invalid runtime: {data.runtime}",
            details={"runtime": data.runtime},
            status_code=422
        )

    # ... rest of logic ...
```

**CLI Error Handling:**

```python
# cli/rgrid/cli.py
@click.command()
def run(script):
    """Run script remotely."""

    try:
        execution = api_client.create_execution(script)
        click.echo(f"✓ Execution started: {execution['id']}")

    except ApiError as e:
        # Parse error response
        error = e.response.json().get('error', {})
        code = error.get('code')
        message = error.get('message')

        # User-friendly error messages
        if code == 'INSUFFICIENT_CREDITS':
            click.echo(f"Error: {message}", err=True)
            click.echo("\nAdd credits: rgrid credits add", err=True)

        elif code == 'AUTHENTICATION_REQUIRED':
            click.echo("Error: Not authenticated", err=True)
            click.echo("Run: rgrid init", err=True)

        else:
            click.echo(f"Error: {message}", err=True)

        sys.exit(1)
```

---

### Decision 12: Logging Format

**Decision:** Structured JSON logging with consistent fields, correlation IDs for request tracing.

**Logging Configuration:**

```python
# api/app/core/logging.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add execution ID if present
        if hasattr(record, 'execution_id'):
            log_data['execution_id'] = record.execution_id

        # Add account ID if present
        if hasattr(record, 'account_id'):
            log_data['account_id'] = record.account_id

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging():
    """Configure structured logging for application."""

    # Create JSON formatter
    formatter = JSONFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler (rotated daily)
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename='/var/log/rgrid/api.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

**Request Correlation:**

```python
# api/app/middleware/correlation.py
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class CorrelationMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests for tracing."""

    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())

        # Attach to request state
        request.state.correlation_id = correlation_id

        # Add to logging context
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record

        logging.setLogRecordFactory(record_factory)

        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host
            }
        )

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers['X-Correlation-ID'] = correlation_id

        # Log response
        logger.info(
            f"Response {response.status_code}",
            extra={
                "status_code": response.status_code,
                "method": request.method,
                "path": request.url.path
            }
        )

        # Restore old factory
        logging.setLogRecordFactory(old_factory)

        return response
```

**Contextual Logging:**

```python
# api/app/services/execution_service.py
import logging

logger = logging.getLogger(__name__)

async def create(db: AsyncSession, account: Account, data: ExecutionCreate):
    """Create execution with contextual logging."""

    logger.info(
        "Creating execution",
        extra={
            "account_id": str(account.id),
            "runtime": data.runtime,
            "timeout_seconds": data.timeout_seconds
        }
    )

    # ... logic ...

    logger.info(
        "Execution created successfully",
        extra={
            "execution_id": str(execution.id),
            "script_hash": execution.script_hash,
            "estimated_cost_microns": execution.estimated_cost_microns
        }
    )

    return execution
```

**Log Output Example:**

```json
{
  "timestamp": "2025-11-15T01:00:00.123456",
  "level": "INFO",
  "logger": "app.services.execution_service",
  "message": "Creating execution",
  "module": "execution_service",
  "function": "create",
  "line": 42,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "acct_abc123",
  "runtime": "python:3.11",
  "timeout_seconds": 300
}
```

**Performance Logging:**

```python
# Log slow operations
import time

async def create(db: AsyncSession, account: Account, data: ExecutionCreate):
    start_time = time.time()

    # ... logic ...

    duration = time.time() - start_time

    if duration > 1.0:  # Log if > 1 second
        logger.warning(
            f"Slow execution creation: {duration:.2f}s",
            extra={
                "duration_seconds": duration,
                "execution_id": str(execution.id)
            }
        )
```

---

## Database Schema

### Complete SQL Schema

```sql
-- See Decision 2 for complete schema
-- Key highlights:

-- Multi-tenant account model
CREATE TABLE accounts (...);
CREATE TABLE users (...);
CREATE TABLE account_memberships (...);

-- Server types (data-driven)
CREATE TABLE server_types (
    server_type VARCHAR(50),
    cpu_cores INTEGER,
    hourly_cost_microns BIGINT,  -- MICRONS!
    max_concurrent_jobs INTEGER GENERATED
);

-- Shared worker pool
CREATE TABLE workers (
    server_type_id UUID REFERENCES server_types,
    current_concurrent_jobs INTEGER,
    available_slots INTEGER GENERATED,
    billing_hour_started_at TIMESTAMP,
    billing_hour_ends_at TIMESTAMP
);

-- Executions (jobs)
CREATE TABLE executions (
    account_id UUID,
    worker_id UUID,
    estimated_cost_microns BIGINT,
    final_cost_microns BIGINT,
    cost_finalized_at TIMESTAMP
);

-- Financial ledger
CREATE TABLE account_credits (
    amount_microns BIGINT,  -- Can be positive or negative
    transaction_type VARCHAR(50)
);

-- Content-hash caching
CREATE TABLE cache_entries (
    cache_type VARCHAR(50),
    content_hash VARCHAR(64),
    docker_image_tag VARCHAR(255),
    last_accessed_at TIMESTAMP
);
```

---

## Component Architecture

### FastAPI Control Plane

**Responsibilities:**
- API endpoints (thin route handlers)
- Authentication (Clerk + API keys)
- Execution lifecycle management
- File upload coordination
- Cost calculation and billing
- WebSocket log streaming

**Key Services:**
- `execution_service.py` - Execution CRUD + Ray submission
- `artifact_service.py` - MinIO integration
- `worker_service.py` - Worker monitoring
- `billing_service.py` - Cost calculation
- `cache_service.py` - Content-hash caching

### Ray Orchestrator

**Responsibilities:**
- Distributed task scheduling
- Worker pool management
- Task retry logic
- Result collection

**Deployment:**
- Head node: Separate container on control plane
- Workers: Join via hardcoded IP

### Worker Provisioner

**Responsibilities:**
- Monitor queue depth
- Provision workers via Hetzner API
- Manage worker lifecycle (TTL)
- Terminate idle workers (after billing hour)

**Scaling Logic:**
- Provision if: no available slots AND queue time > 10 min
- Terminate if: billing hour expired AND idle AND no pending jobs

### Docker Executor (Runner)

**Responsibilities:**
- Pull/build Docker images
- Execute user scripts in containers
- Capture stdout/stderr
- Upload outputs to MinIO

**Isolation:**
- No network by default (Free tier)
- Read-only root filesystem
- Resource limits (CPU, memory)
- Timeout enforcement

---

## Deployment Architecture

### All-Hetzner MVP Setup

**Control Plane: Hetzner CX31** (~€6.45/month)
- 2 vCPU, 8GB RAM, 80GB disk
- Runs all core services via Docker Compose
- Private network IP: 10.0.0.1

```yaml
# infra/docker-compose.yml
version: '3.8'
services:
  api:
    build: ./api
    environment:
      - RAY_ADDRESS=ray://ray-head:10001
      - DATABASE_URL=postgresql://postgres:password@db:5432/rgrid
      - MINIO_URL=http://minio:9000
    ports:
      - "8000:8000"

  website:
    build:
      context: ./website
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.rgrid.dev
      - NEXT_PUBLIC_CONSOLE_URL=https://app.rgrid.dev
    ports:
      - "3000:3000"
    restart: unless-stopped

  console:
    build:
      context: ./console
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.rgrid.dev
      - NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${CLERK_PUBLISHABLE_KEY}
      - CLERK_SECRET_KEY=${CLERK_SECRET_KEY}
    ports:
      - "3001:3000"
    restart: unless-stopped

  ray-head:
    image: rayproject/ray:latest
    command: ray start --head --port=6379 --dashboard-host=0.0.0.0
    ports:
      - "8265:8265"
      - "10001:10001"

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=rgrid
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"

  registry:
    image: registry:2
    environment:
      REGISTRY_STORAGE: s3
      REGISTRY_STORAGE_S3_ENDPOINT: minio:9000
      REGISTRY_STORAGE_S3_BUCKET: docker-images
    ports:
      - "5000:5000"

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - certbot_data:/etc/letsencrypt
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - website
      - console

volumes:
  postgres_data:
  minio_data:
  certbot_data:
```

**Worker Nodes: Hetzner CX22** (~€0.005/hour, auto-scaled)
- 2 vCPU, 4GB RAM, 40GB disk
- Ephemeral (60 min lifetime)
- Join Ray cluster via cloud-init

```yaml
# infra/cloud-init.yml
#cloud-config
packages:
  - docker.io

runcmd:
  - docker run -d --name ray-worker --network=host \
      rayproject/ray:latest \
      ray start \
        --address=10.0.0.1:6379 \
        --num-cpus=2 \
        --memory=4000000000 \
        --block
```

**Nginx Configuration (Domain Routing):**

```nginx
# infra/nginx.conf
events {
    worker_connections 1024;
}

http {
    # Marketing website: rgrid.dev
    server {
        listen 80;
        server_name rgrid.dev www.rgrid.dev;

        location / {
            proxy_pass http://website:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }

    # Console: app.rgrid.dev
    server {
        listen 80;
        server_name app.rgrid.dev;

        location / {
            proxy_pass http://console:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }

    # API: api.rgrid.dev
    server {
        listen 80;
        server_name api.rgrid.dev;

        location / {
            proxy_pass http://api:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support for real-time logs
        location /ws {
            proxy_pass http://api:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }

    # SSL will be added via certbot (commented out for initial setup)
    # After certbot runs, it will add:
    # - listen 443 ssl;
    # - ssl_certificate /etc/letsencrypt/live/rgrid.dev/fullchain.pem;
    # - ssl_certificate_key /etc/letsencrypt/live/rgrid.dev/privkey.pem;
}
```

**Deployment Process:**

```bash
# 1. Create Hetzner control plane server (manual, one-time)
# 2. SSH into server
ssh root@control-plane-ip

# 3. Clone repo
git clone https://github.com/yourusername/rgrid
cd rgrid

# 4. Configure environment
cp .env.example .env
nano .env  # Set secrets

# 5. Deploy
docker-compose up -d

# 6. Setup SSL (for all three domains)
docker-compose exec nginx certbot --nginx \
  -d rgrid.dev -d www.rgrid.dev \
  -d app.rgrid.dev \
  -d api.rgrid.dev
```

**CI/CD (GitHub Actions):**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Hetzner
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HETZNER_SERVER_IP }}
          username: root
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/rgrid
            git pull
            docker-compose pull
            docker-compose up -d --build
```

---

## Security Architecture

### Authentication

**Web Console:**
- Clerk OIDC
- JWT session tokens
- Multi-factor authentication (optional)

**CLI:**
- API keys (bcrypt hashed)
- Stored in `~/.rgrid/credentials` (0600 permissions)
- Never logged or exposed

### Authorization

**Account-based:**
- Users belong to accounts via memberships
- Resources (executions, artifacts) scoped to accounts
- API keys belong to accounts (not users)

### Network Security

**Free Tier:**
- No network access in containers (`--network=none`)

**Verified Tier:**
- Network enabled with monitoring
- Rate limiting: 1000 req/min
- Blocked ports: 25, 445, 1433, 3306, 3389

**Trusted Tier:**
- Relaxed limits (10,000 req/min)

### Container Isolation

- Read-only root filesystem
- No privileged mode
- Resource limits (CPU, memory)
- Timeout enforcement
- User namespace isolation

### Data Security

**At Rest:**
- PostgreSQL encryption (provider default)
- MinIO encryption (optional S3 SSE)

**In Transit:**
- TLS for all API calls
- SSL for database connections
- Presigned URLs for direct MinIO access

### Secrets Management

**Control Plane:**
- Environment variables (Docker secrets)
- Never committed to git

**Workers:**
- No persistent secrets
- Ephemeral (60 min lifetime)

---

## Implementation Guidelines

### Development Workflow

1. **Local Development:**
   ```bash
   # Start all services
   docker-compose -f docker-compose.dev.yml up

   # Install CLI for development
   cd cli && pip install -e .

   # Run tests
   pytest
   ```

2. **Testing:**
   - Unit tests: `pytest tests/`
   - Integration tests: `pytest tests/test_e2e.py`
   - Manual testing: Use CLI against local API

3. **Code Review:**
   - All PRs require approval
   - LLM agents can generate tests
   - Follow existing patterns

### Deployment Checklist

- [ ] Configure environment variables
- [ ] Setup Hetzner API token
- [ ] Configure Clerk application
- [ ] Setup Stripe account
- [ ] Configure DNS (Cloudflare)
- [ ] Deploy control plane
- [ ] Test worker provisioning
- [ ] Configure monitoring (optional)
- [ ] Setup backups (Postgres, MinIO)

### Monitoring (Optional for MVP)

**Metrics to Track:**
- Active workers
- Queue depth
- Execution success rate
- Average execution time
- Cost per execution
- Cache hit rate

**Tools:**
- Prometheus + Grafana (optional)
- Ray dashboard (built-in)
- Application logs (JSON structured)

### Test-Driven Development Strategy

**Requirement: 100% TDD for all production code**

RGrid follows strict test-driven development to enable autonomous agentic development with test agents and dev agents working in collaboration.

#### Test-First Workflow

**Red → Green → Refactor Cycle:**

1. **Red Phase (Test Agent):**
   - Write failing test that describes expected behavior
   - Test should fail for the right reason (not syntax error)
   - Define acceptance criteria as testable assertions

2. **Green Phase (Dev Agent):**
   - Implement minimum code to make test pass
   - No additional features beyond what tests require
   - Run tests incrementally after each file

3. **Refactor Phase (Dev Agent):**
   - Improve code quality while keeping tests green
   - Extract duplicated code
   - Apply SOLID principles
   - Ensure file size stays under 150 lines

#### Test Structure and Organization

**Test Categories:**

```
tests/
├── unit/                    # Pure function tests (no I/O, fast)
│   ├── services/
│   │   ├── test_execution_service.py
│   │   ├── test_billing_service.py
│   │   └── test_cache_service.py
│   ├── models/
│   │   └── test_money.py
│   └── utils/
│       └── test_validators.py
├── integration/             # API endpoints with test database
│   ├── test_executions_api.py
│   ├── test_auth_api.py
│   └── test_artifacts_api.py
├── e2e/                     # CLI commands against local stack
│   ├── test_cli_run.py
│   ├── test_cli_logs.py
│   └── test_batch_execution.py
└── conftest.py              # Shared fixtures
```

**Test Framework Stack:**

- **Backend:** pytest + pytest-asyncio + pytest-mock + pytest-cov
- **Frontend:** Jest + React Testing Library + MSW (Mock Service Worker)
- **E2E:** Playwright (for CLI automation against Docker Compose stack)

#### Test Coverage Requirements

**Minimum Coverage Standards:**

- **Service Layer:** 100% coverage (critical business logic)
- **API Routes:** 95% coverage (HTTP handlers)
- **Database Models:** 90% coverage (SQLAlchemy models)
- **Frontend Components:** 80% coverage (React components)
- **CLI Commands:** 90% coverage (Click commands)

**Excluded from Coverage:**
- Type stubs (`.pyi` files)
- Test fixtures (`conftest.py`)
- Configuration files
- Migration scripts

**Coverage Enforcement:**

```bash
# Run tests with coverage report
pytest --cov=api --cov-report=term-missing --cov-fail-under=95

# Generate HTML coverage report
pytest --cov=api --cov-report=html

# Pre-commit hook checks coverage
.git/hooks/pre-commit:
  pytest --cov=api --cov-fail-under=95 || exit 1
```

#### Agent Collaboration Protocol

**Test Agent Responsibilities:**

1. Read story acceptance criteria
2. Write failing tests for each acceptance criterion
3. Organize tests by unit/integration/e2e category
4. Commit tests with message: "Tests for [story-name] - all failing"
5. Exit when all tests written and fail correctly

**Dev Agent Responsibilities:**

1. Read failing tests from Test Agent commit
2. Implement code to pass tests incrementally
3. Run `pytest tests/unit/test_feature.py` after each file
4. Ensure no file exceeds 150 lines
5. Commit implementation with message: "Implementation for [story-name] - all tests passing"
6. Exit when all tests pass

**Review Agent Responsibilities:**

1. Read implementation + tests from Dev Agent commit
2. Validate test coverage ≥95% (`pytest --cov`)
3. Validate no files >150 lines (`find . -name "*.py" -exec wc -l {} \; | awk '$1 > 150'`)
4. Check for code smells (deep nesting, complex conditionals)
5. Verify type hints present (`mypy --strict`)
6. Approve merge or request refactor

#### Test Fixtures and Mocking

**Database Fixtures:**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from api.app.db.session import Base

@pytest.fixture
async def test_db():
    """Create test database with schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
async def test_account(test_db):
    """Create test account."""
    account = Account(
        id=uuid4(),
        name="Test Account",
        credit_balance_microns=1_000_000  # €1.00
    )
    test_db.add(account)
    await test_db.commit()
    return account
```

**API Mocking:**

```python
# tests/unit/services/test_execution_service.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_create_execution_insufficient_credits():
    """Test execution creation fails with insufficient credits."""
    # Arrange
    mock_db = AsyncMock()
    account = Account(credit_balance_microns=100)  # Only 0.0001 EUR
    execution_data = ExecutionCreate(
        script_content="print('hello')",
        runtime="python:3.11"
    )

    # Act & Assert
    with pytest.raises(InsufficientCreditsError):
        await execution_service.create(mock_db, account, execution_data)
```

#### TDD Best Practices for AI Agents

**1. Test Names Are Documentation:**

```python
# Good: Describes what should happen
def test_create_execution_deducts_credits_from_account():
    pass

# Bad: Generic test name
def test_execution():
    pass
```

**2. Arrange-Act-Assert Pattern:**

```python
def test_billing_hour_optimization():
    # Arrange: Set up test data
    worker = Worker(billing_hour_ends_at=datetime.utcnow() + timedelta(minutes=5))

    # Act: Execute the function
    should_terminate, reason = should_terminate_worker(worker)

    # Assert: Verify expected behavior
    assert should_terminate is False
    assert "Within billing hour" in reason
```

**3. One Assertion Per Test (Preferred):**

```python
# Good: Focused test
def test_money_class_converts_micros_to_euros():
    money = Money(micros=1_000_000)
    assert money.to_units() == 1.0

def test_money_class_formats_with_euro_symbol():
    money = Money(micros=1_500_000, currency='EUR')
    assert money.format() == "€1.5"
```

**4. Test Edge Cases:**

```python
def test_execution_timeout_enforced():
    """Test execution killed after timeout."""
    pass

def test_execution_with_zero_credit_balance_fails():
    """Test execution rejected with 0 credits."""
    pass

def test_worker_provisioning_when_queue_empty():
    """Test no workers provisioned when queue is empty."""
    pass
```

### File Size Constraints (Extreme Decomposition)

**Hard Limit: 150 lines per file (including whitespace and comments)**

RGrid enforces strict file size limits to enable AI agents to work effectively with small context windows and to maintain clear single-responsibility principle.

#### Enforcement Mechanisms

**1. Pre-Commit Hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking file size constraints..."

# Find all Python files >150 lines
violations=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec wc -l {} \; | awk '$1 > 150 {print $2 " (" $1 " lines)"}')

if [ -n "$violations" ]; then
    echo "❌ File size limit violated (150 lines max):"
    echo "$violations"
    exit 1
fi

echo "✅ All files within 150 line limit"
```

**2. Linting Rule (flake8):**

```ini
# setup.cfg or .flake8
[flake8]
max-line-length = 120
max-file-lines = 150
exclude = venv,.venv,tests/fixtures
```

**3. CI/CD Check:**

```yaml
# .github/workflows/ci.yml
- name: Check file size limits
  run: |
    violations=$(find . -name "*.py" -exec wc -l {} \; | awk '$1 > 150')
    if [ -n "$violations" ]; then
      echo "File size violations detected"
      exit 1
    fi
```

#### Decomposition Patterns

**Pattern 1: One Public Function Per File**

```python
# ❌ BAD: Multiple functions in one file (200 lines)
# api/app/services/execution_service.py
async def create(db, account, data):
    # 80 lines of logic
    pass

async def get(db, execution_id):
    # 40 lines of logic
    pass

async def list_executions(db, account_id):
    # 50 lines of logic
    pass

async def cancel(db, execution_id):
    # 30 lines of logic
    pass
```

```python
# ✅ GOOD: One function per file
# api/app/services/execution_service/create.py (80 lines)
async def create(db, account, data):
    # 80 lines of logic
    pass

# api/app/services/execution_service/get.py (40 lines)
async def get(db, execution_id):
    # 40 lines of logic
    pass

# api/app/services/execution_service/list.py (50 lines)
async def list_executions(db, account_id):
    # 50 lines of logic
    pass

# api/app/services/execution_service/cancel.py (30 lines)
async def cancel(db, execution_id):
    # 30 lines of logic
    pass

# api/app/services/execution_service/__init__.py (10 lines)
from .create import create
from .get import get
from .list import list_executions
from .cancel import cancel

__all__ = ['create', 'get', 'list_executions', 'cancel']
```

**Pattern 2: Extract Private Helpers**

```python
# ❌ BAD: Complex function with helpers in same file (180 lines)
# api/app/services/execution_service/create.py
async def create(db, account, data):
    # Validate credits
    required_cost = _calculate_cost(data)
    if account.credit_balance_microns < required_cost:
        raise InsufficientCreditsError()

    # Upload script
    script_key = _upload_script(data.script_content)

    # Create execution
    execution = _create_execution_record(db, account, script_key)

    # Submit to Ray
    await _submit_to_ray(execution.id)

    return execution

def _calculate_cost(data):
    # 40 lines
    pass

def _upload_script(content):
    # 30 lines
    pass

def _create_execution_record(db, account, script_key):
    # 50 lines
    pass

async def _submit_to_ray(execution_id):
    # 40 lines
    pass
```

```python
# ✅ GOOD: Extract helpers to separate files
# api/app/services/execution_service/create.py (40 lines)
from ._calculate_cost import calculate_cost
from ._upload_script import upload_script
from ._create_record import create_execution_record
from ._submit_to_ray import submit_to_ray

async def create(db, account, data):
    required_cost = await calculate_cost(data)
    if account.credit_balance_microns < required_cost:
        raise InsufficientCreditsError()

    script_key = await upload_script(data.script_content)
    execution = await create_execution_record(db, account, script_key)
    await submit_to_ray(execution.id)

    return execution

# api/app/services/execution_service/_calculate_cost.py (40 lines)
async def calculate_cost(data):
    # 40 lines of cost calculation logic
    pass

# api/app/services/execution_service/_upload_script.py (30 lines)
async def upload_script(content):
    # 30 lines of MinIO upload logic
    pass

# api/app/services/execution_service/_create_record.py (50 lines)
async def create_execution_record(db, account, script_key):
    # 50 lines of database logic
    pass

# api/app/services/execution_service/_submit_to_ray.py (40 lines)
async def submit_to_ray(execution_id):
    # 40 lines of Ray submission logic
    pass
```

**Pattern 3: One API Endpoint Per File**

```python
# ✅ GOOD: One endpoint per file
# api/app/api/v1/executions/create.py (80 lines)
from fastapi import APIRouter, Depends
from app.services.execution_service import create

router = APIRouter()

@router.post("", response_model=Execution, status_code=201)
async def create_execution(
    execution_data: ExecutionCreate,
    account: Account = Depends(get_authenticated_account)
):
    """Create a new execution."""
    return await create.create(db, account, execution_data)

# api/app/api/v1/executions/get.py (40 lines)
@router.get("/{execution_id}", response_model=Execution)
async def get_execution(execution_id: UUID):
    """Get execution by ID."""
    return await get.get(db, execution_id)

# api/app/api/v1/executions/__init__.py (20 lines)
from fastapi import APIRouter
from .create import router as create_router
from .get import router as get_router

router = APIRouter(prefix="/executions", tags=["executions"])
router.include_router(create_router)
router.include_router(get_router)
```

**Pattern 4: One Database Model Per File**

```python
# ✅ GOOD: One model per file
# api/app/db/models/execution.py (<150 lines)
from sqlalchemy import Column, String, BigInteger, ForeignKey
from api.app.db.base import Base

class Execution(Base):
    __tablename__ = "executions"

    id = Column(UUID, primary_key=True)
    account_id = Column(UUID, ForeignKey("accounts.id"))
    script_hash = Column(String(64))
    estimated_cost_microns = Column(BigInteger)
    # ... rest of model definition

# api/app/db/models/account.py (<150 lines)
class Account(Base):
    __tablename__ = "accounts"
    # ... model definition
```

**Pattern 5: React Components (Stricter - 100 Lines Max)**

```typescript
// ✅ GOOD: Small, focused components
// console/components/JobsList.tsx (85 lines)
export function JobsList({ jobs }: JobsListProps) {
  return (
    <div className="space-y-4">
      {jobs.map(job => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  )
}

// console/components/JobCard.tsx (60 lines)
export function JobCard({ job }: JobCardProps) {
  return (
    <Card>
      <CardHeader>
        <JobStatus status={job.status} />
      </CardHeader>
      {/* ... */}
    </Card>
  )
}

// console/components/JobStatus.tsx (40 lines)
export function JobStatus({ status }: JobStatusProps) {
  const Icon = getStatusIcon(status)
  return <Badge><Icon />{status}</Badge>
}
```

#### Additional Constraints

**Function Complexity Limits:**

- **Max 20 lines per function** (public functions)
- **Max 4 parameters per function** (use objects for >4)
- **Cyclomatic complexity < 5** (max 4 decision points)
- **Nesting depth ≤ 3 levels** (avoid deep if/for nesting)

**Example:**

```python
# ❌ BAD: Too many parameters, too complex
def create_execution(db, account_id, script_content, runtime, timeout, cpu, memory, env_vars):
    if account_id:
        if db.query(Account).filter_by(id=account_id).first():
            if script_content:
                # 8 levels of nesting...
                pass

# ✅ GOOD: Object parameter, flat structure
async def create(db: AsyncSession, data: ExecutionCreateData) -> Execution:
    account = await validate_account(db, data.account_id)
    script = await validate_script(data.script_content)
    execution = await build_execution(account, script, data.config)
    return await save_execution(db, execution)
```

#### Benefits for AI Agents

**1. Small Context Windows:**
- 150-line files fit entirely in agent context
- Agents can understand entire file at once
- No need to scroll or paginate

**2. Clear Single Responsibility:**
- Each file does ONE thing
- Easier to name files descriptively
- Less cognitive load for agents

**3. Minimal Merge Conflicts:**
- Different agents work on different files
- Parallel development without conflicts
- Clear file boundaries

**4. Fast Navigation:**
- `execution_service/create.py` clearly indicates purpose
- No searching within large files
- File tree mirrors architecture

### Agentic Development Workflow

**Team: Test Agent, Dev Agent, Review Agent**

RGrid uses a multi-agent workflow where specialized agents collaborate to implement user stories following strict test-driven development.

#### Story Execution Flow

**Phase 1: Story Breakdown (PM/Architect Agent)**

**Input:** Epic with high-level requirements

**Output:** User story with acceptance criteria

**Format:**

```markdown
# Story: Create execution endpoint

## Acceptance Criteria

1. **GIVEN** a valid ExecutionCreate request with sufficient credits
   **WHEN** POST /v1/executions is called
   **THEN** return 201 with Execution object

2. **GIVEN** an ExecutionCreate request with insufficient credits
   **WHEN** POST /v1/executions is called
   **THEN** return 402 with INSUFFICIENT_CREDITS error

3. **GIVEN** an invalid ExecutionCreate request
   **WHEN** POST /v1/executions is called
   **THEN** return 422 with VALIDATION_ERROR

## File Manifest

**Files to Create:** (estimated lines)
- `api/app/api/v1/executions/create.py` (80 lines)
- `api/app/services/execution_service/create.py` (60 lines)
- `api/app/services/execution_service/_validate_credits.py` (30 lines)
- `tests/integration/test_executions_api.py` (120 lines)
- `tests/unit/services/test_execution_service.py` (90 lines)

**Files to Modify:**
- `api/app/api/v1/__init__.py` (add router import)

**Total Estimated Lines:** ~380 lines across 6 files
```

**Phase 2: Test Agent (Writes Failing Tests)**

**Input:** Acceptance criteria from story

**Responsibilities:**

1. Read acceptance criteria
2. Write failing tests for each criterion
3. Organize tests by category (unit/integration/e2e)
4. Use Given/When/Then format in test docstrings
5. Commit tests with descriptive message

**Example Test Output:**

```python
# tests/integration/test_executions_api.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_create_execution_with_sufficient_credits():
    """
    GIVEN a valid ExecutionCreate request with sufficient credits
    WHEN POST /v1/executions is called
    THEN return 201 with Execution object
    """
    # Arrange
    client = TestClient(app)
    account = await create_test_account(credit_balance_microns=1_000_000)

    # Act
    response = client.post(
        "/v1/executions",
        json={
            "script_content": "print('hello')",
            "runtime": "python:3.11"
        },
        headers={"X-API-Key": account.api_key}
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["script_hash"] is not None

@pytest.mark.asyncio
async def test_create_execution_insufficient_credits():
    """
    GIVEN an ExecutionCreate request with insufficient credits
    WHEN POST /v1/executions is called
    THEN return 402 with INSUFFICIENT_CREDITS error
    """
    # Arrange
    account = await create_test_account(credit_balance_microns=0)

    # Act
    response = client.post("/v1/executions", ...)

    # Assert
    assert response.status_code == 402
    assert response.json()["error"]["code"] == "INSUFFICIENT_CREDITS"
```

**Exit Criteria:**
- All acceptance criteria have corresponding tests
- All tests fail with expected error messages
- Tests are organized in correct directories
- Git commit message: "Tests for [story-name] - all failing (Red phase)"

**Phase 3: Dev Agent (Implements Code to Pass Tests)**

**Input:** Failing tests from Test Agent commit

**Responsibilities:**

1. Read failing tests to understand requirements
2. Implement code incrementally (one file at a time)
3. Run `pytest tests/unit/test_file.py` after each file
4. Ensure no file exceeds 150 lines (decompose if needed)
5. Add type hints and docstrings
6. Commit when all tests pass

**Implementation Strategy:**

```bash
# Dev Agent workflow
1. Read failing tests
2. Implement service layer (business logic)
   - Create execution_service/create.py
   - Run: pytest tests/unit/services/test_execution_service.py
   - Status: Some tests passing (service layer working)

3. Implement API route (HTTP handler)
   - Create api/v1/executions/create.py
   - Run: pytest tests/integration/test_executions_api.py
   - Status: All tests passing

4. Verify file sizes
   - Run: find . -name "*.py" -exec wc -l {} \; | awk '$1 > 150'
   - Fix: Extract helpers if any file >150 lines

5. Run full test suite
   - Run: pytest --cov=api --cov-fail-under=95
   - Status: All tests green, coverage ≥95%

6. Commit implementation
   - Message: "Implementation for [story-name] - all tests passing (Green phase)"
```

**Exit Criteria:**
- All tests from Test Agent are passing
- No files exceed 150 lines
- Code coverage ≥95%
- Type hints present on all functions
- Git commit message: "Implementation for [story-name] - all tests passing (Green phase)"

**Phase 4: Review Agent (Validates Quality)**

**Input:** Implementation + tests from Dev Agent commit

**Responsibilities:**

1. Validate test coverage (`pytest --cov --cov-fail-under=95`)
2. Validate file sizes (`find . -name "*.py" -exec wc -l {} \;`)
3. Check code quality (complexity, nesting, naming)
4. Verify type hints (`mypy --strict`)
5. Check for code smells
6. Approve or request refactor

**Quality Checklist:**

```yaml
- [ ] All tests passing (pytest)
- [ ] Test coverage ≥95% (pytest --cov)
- [ ] No files >150 lines (wc -l)
- [ ] No functions >20 lines
- [ ] No functions with >4 parameters
- [ ] Cyclomatic complexity <5 (radon cc)
- [ ] Type hints present (mypy --strict)
- [ ] Docstrings for public functions
- [ ] No code smells:
  - [ ] Deep nesting (≤3 levels)
  - [ ] Magic numbers (use constants)
  - [ ] Duplicated code (extract helpers)
  - [ ] Unclear variable names
```

**Exit Criteria:**
- All quality checks pass
- Refactor complete if issues found
- Git commit approved for merge to main

#### Handoff Protocol

**Test Agent → Dev Agent:**

```bash
# Test Agent commits
git add tests/
git commit -m "Tests for create-execution-endpoint - all failing (Red phase)

Acceptance Criteria:
- AC1: Valid request returns 201 with Execution
- AC2: Insufficient credits returns 402 error
- AC3: Invalid request returns 422 error

Tests Written:
- tests/integration/test_executions_api.py (3 tests)
- tests/unit/services/test_execution_service.py (2 tests)

Status: All tests failing as expected"

git push
```

**Dev Agent → Review Agent:**

```bash
# Dev Agent commits
git add api/ tests/
git commit -m "Implementation for create-execution-endpoint - all tests passing (Green phase)

Files Created:
- api/app/api/v1/executions/create.py (78 lines)
- api/app/services/execution_service/create.py (58 lines)
- api/app/services/execution_service/_validate_credits.py (28 lines)

Test Results:
- pytest: 5/5 tests passing
- coverage: 97% (target: 95%)
- file sizes: all <150 lines

Status: Ready for review"

git push
```

**Review Agent → Next Story:**

```bash
# Review Agent approves
git merge feature/create-execution-endpoint

# Or requests refactor
git comment "Refactor required:
- execution_service/create.py has cyclomatic complexity 8 (max: 5)
- Extract conditional logic to separate validation function"
```

#### Context Files for Agents

**Required Reading for All Agents:**

1. `docs/architecture.md` - Technical architecture and patterns
2. `docs/PRD.md` - Product requirements (for context)
3. Story acceptance criteria (specific to current story)

**Optional Reading (as needed):**

- Related code files (for understanding existing patterns)
- Test fixtures (`tests/conftest.py`)
- Database models (`api/app/db/models/`)

**Agent Context Window Strategy:**

- Each agent works with ≤10 files at a time
- Files are ≤150 lines each = ≤1,500 lines total context
- Well within Claude's context window (200K tokens)

#### Multi-Agent Parallel Development

**Story Parallelization:**

Different agents can work on independent stories simultaneously:

```
Week 1:
- Story A (create-execution): Test Agent → Dev Agent → Review Agent
- Story B (list-executions): Test Agent (parallel) → waiting
- Story C (get-execution): waiting

Week 2:
- Story A: ✅ Merged
- Story B: Dev Agent → Review Agent
- Story C: Test Agent → Dev Agent
```

**Conflict Avoidance:**

- Stories assigned to different file areas (no overlap)
- File-per-function pattern minimizes conflicts
- Clear file manifest in each story

---

## Future Evolution Paths

### Execution Model Abstraction (EMA)

**Current:** Ray
**Future:** Temporal, Inngest, Kubernetes, serverless

**Abstraction Layer:**
```python
# api/app/orchestration/base.py
class ExecutionBackend(ABC):
    @abstractmethod
    async def submit(self, execution: Execution) -> str:
        """Submit execution, return task ID."""
        pass

    @abstractmethod
    async def get_status(self, task_id: str) -> str:
        """Get execution status."""
        pass

# api/app/orchestration/ray_backend.py
class RayBackend(ExecutionBackend):
    async def submit(self, execution: Execution) -> str:
        result_ref = execute_job.remote(...)
        return result_ref.task_id().hex()

# Future: app/orchestration/temporal_backend.py
class TemporalBackend(ExecutionBackend):
    async def submit(self, execution: Execution) -> str:
        workflow_id = await temporal_client.start_workflow(...)
        return workflow_id
```

### Cloud Provider Abstraction (CPAL)

**Current:** Hetzner only
**Future:** AWS, GCP, Fly.io, BYOC

**Abstraction Layer:**
```python
# orchestrator/providers/base.py
class CloudProvider(ABC):
    @abstractmethod
    async def provision_worker(self, server_type: str) -> Worker:
        pass

    @abstractmethod
    async def terminate_worker(self, worker_id: str):
        pass

# orchestrator/providers/hetzner.py
class HetznerProvider(CloudProvider):
    async def provision_worker(self, server_type: str):
        server = hetzner_client.servers.create(...)
        return Worker(...)

# Future: orchestrator/providers/aws.py
class AWSProvider(CloudProvider):
    async def provision_worker(self, server_type: str):
        instance = ec2_client.run_instances(...)
        return Worker(...)
```

### Runtime Plugin Architecture

**Current:** Hardcoded runtimes (python:3.11, ffmpeg:latest)
**Future:** User-provided runtimes, GPU support

```python
# Runtime registry
RUNTIMES = {
    "python:3.11": {"base_image": "python:3.11-slim"},
    "python:3.11-gpu": {"base_image": "nvidia/cuda:12.0-python3.11"},
    "ffmpeg:latest": {"base_image": "jrottenberg/ffmpeg:latest"},
    # Future: User-provided
    "custom:my-runtime": {"base_image": "account_abc123/my-runtime:v1"}
}
```

### Workflow Orchestration

**Current:** Single script execution
**Future:** Multi-step DAGs, dependencies, triggers

```python
# Future: workflow.yaml
name: video-processing-pipeline
steps:
  - name: extract-audio
    script: extract_audio.py
    runtime: ffmpeg:latest

  - name: transcribe
    script: transcribe.py
    runtime: python:3.11-gpu
    depends_on: [extract-audio]

  - name: generate-subtitles
    script: subtitles.py
    depends_on: [transcribe]
```

---

## Appendix

### Technology Choices Rationale

**Python vs Go:**
- Python for MVP: Faster development, Ray integration
- Go for production: CLI rewrite for performance (optional)

**Ray vs Temporal:**
- Ray for MVP: Simpler, Python-native, battle-tested
- Temporal for growth: Workflow-heavy use cases

**Hetzner vs AWS:**
- Hetzner for MVP: 1/3 cost, simpler API
- AWS for scale: Global availability, more services

**MinIO vs S3:**
- MinIO for MVP: Self-hosted, cost control
- S3/R2 for scale: Zero egress fees (Cloudflare R2)

### Glossary

- **Account:** Billing entity (team/organization)
- **Execution:** Single script run (job)
- **Worker:** Ephemeral compute node (Hetzner CX22)
- **Micron:** 1/1,000,000 of currency unit (€0.000001)
- **Script Hash:** SHA256 of script content (for caching)
- **Billing Hour:** 60-minute window for worker cost optimization
- **EMA:** Execution Model Abstraction (Ray, Temporal, etc.)
- **CPAL:** Cloud Provider Abstraction Layer (Hetzner, AWS, etc.)

---

**Document End**

This architecture is ready for implementation. All major decisions documented, patterns established, and abstractions defined for future growth.
