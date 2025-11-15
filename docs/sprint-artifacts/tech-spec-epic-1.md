# Epic Technical Specification: Foundation & CLI Core

Date: 2025-11-15
Author: BMad
Epic ID: 1
Status: Draft

---

## Overview

Epic 1 establishes the foundational infrastructure for the RGrid distributed compute platform. This epic delivers the core project structure, development environment, CLI framework, and authentication system that all subsequent epics depend upon. The primary goal is to enable developers to authenticate via API keys and execute basic CLI commands against a FastAPI backend with PostgreSQL and MinIO storage. This epic implements the "Dropbox Simplicity for Developers" philosophy from the PRD by providing a clean, intuitive developer experience from the first `rgrid init` command.

The epic covers monorepo initialization, automated build/test/lint tooling, secure API key authentication (following AWS credentials pattern), Click-based CLI framework, the critical `rgrid init` command for sub-60-second authentication setup, and a FastAPI backend with database connectivity—all designed with LLM-agent-friendly code patterns for future maintainability.

## Objectives and Scope

### In Scope

**FR Coverage:** FR1, FR2, FR51, FR52, FR53, FR54, FR55

- **Monorepo Structure** (Story 1.1): Establish `api/`, `orchestrator/`, `runner/`, `cli/`, `console/`, `website/`, `common/`, `infra/`, `tests/`, `docs/` directories with proper Python dependency management
- **Development Environment** (Story 1.2): Docker Compose for PostgreSQL + MinIO, Makefile automation (setup, test, lint, format), pre-commit hooks (black, ruff, mypy), 80% test coverage enforcement
- **API Key Authentication** (Story 1.3): bcrypt-hashed API keys with `sk_live_` prefix, FastAPI dependency injection for route protection, `~/.rgrid/credentials` storage (never in git)
- **CLI Framework** (Story 1.4): Click-based command structure, credential loading, httpx HTTP client, user-friendly error messages (no stack traces), stub commands for init, run, status, logs
- **rgrid init Command** (Story 1.5): Interactive API key setup with validation via `POST /api/v1/auth/validate`, sub-30-second execution, secure input (no echo), overwrite protection
- **FastAPI Backend** (Story 1.6): SQLAlchemy 2.0 + asyncpg ORM, MinIO client initialization, `/health` endpoint, `/api/v1/auth/validate` endpoint, Pydantic request/response models, Alembic migrations

### Out of Scope

- Script execution functionality (Epic 2)
- Ray cluster setup (Epic 3)
- Hetzner provisioning (Epic 4)
- Batch operations (Epic 5)
- Caching mechanisms (Epic 6)
- File upload/download beyond basic MinIO initialization (Epic 7)
- WebSocket log streaming (Epic 8)
- Cost tracking/billing logic (Epic 9)
- Web console UI (Epic 10)
- Production deployment configuration (covered in later epic tech specs)

## System Architecture Alignment

Epic 1 directly implements foundational architecture decisions:

- **Decision 1: Project Structure** - Monorepo with shared Python package (`common/`) installable via `pip install -e`, enabling code reuse across api/, cli/, orchestrator/, runner/ components
- **Decision 6: Authentication** - API Keys authentication pattern following AWS credentials model, storing keys in `~/.rgrid/credentials` (never in project files), bcrypt hashing for secure storage
- **Decision 7: API Route Structure** - LLM-agent-friendly code patterns throughout: stable folder structure (`api/routes/`, `api/services/`, `api/schemas/`), Pydantic everywhere for type safety, pure service functions separated from HTTP handlers, explicit SQLAlchemy types, comprehensive OpenAPI docs
- **Decision 2: Database Schema** - Initial schema includes `accounts`, `users`, `account_memberships` (Jumpstart multi-tenancy pattern), and `api_keys` tables with BIGINT for cost tracking in micros

**Key Constraints:**
- All costs stored as BIGINT micros (1 EUR = 1,000,000 micros) from Day 1, even though billing logic comes in Epic 9
- Database uses PostgreSQL with asyncpg for async operations
- MinIO initialized for S3-compatible storage (file operations in Epic 7)
- All code follows 10 LLM-agent-friendly principles for future maintainability

## Detailed Design

### Services and Modules

| Module | Responsibility | Key Inputs | Key Outputs | Owner/Layer |
|--------|---------------|------------|-------------|-------------|
| `cli/rgrid/` | CLI entry point, command routing | User commands, `~/.rgrid/credentials` | HTTP requests to API, formatted output | CLI Layer |
| `cli/rgrid/commands/init.py` | Handle `rgrid init` authentication setup | User API key input | Validated credentials file | CLI Layer |
| `cli/rgrid/commands/run.py` | Handle `rgrid run` (stub in Epic 1) | Script path, args | Execution ID | CLI Layer |
| `cli/rgrid/commands/status.py` | Handle `rgrid status` (stub in Epic 1) | Execution ID | Status display | CLI Layer |
| `cli/rgrid/commands/logs.py` | Handle `rgrid logs` (stub in Epic 1) | Execution ID | Log output | CLI Layer |
| `cli/rgrid/client.py` | HTTP client wrapper using httpx | API endpoint, credentials | JSON responses | CLI Layer |
| `api/main.py` | FastAPI application, lifespan events | Environment config | Uvicorn ASGI app | API Layer |
| `api/routes/auth.py` | Authentication endpoints | API key in header | Account info, validation result | API Layer |
| `api/routes/health.py` | Health check endpoint | DB/MinIO connection status | Health JSON | API Layer |
| `api/services/auth_service.py` | Authentication business logic (pure functions) | API key, account ID | Account model, validation result | Service Layer |
| `api/schemas/auth.py` | Pydantic models for auth requests/responses | N/A | Type-safe data models | Schema Layer |
| `api/models/account.py` | SQLAlchemy Account model | N/A | ORM model for accounts table | Data Layer |
| `api/models/api_key.py` | SQLAlchemy APIKey model | N/A | ORM model for api_keys table | Data Layer |
| `api/database.py` | Database connection pool, session management | `DATABASE_URL` env var | AsyncSession factory | Infrastructure |
| `api/storage.py` | MinIO client initialization | `MINIO_*` env vars | MinIO client instance | Infrastructure |
| `common/` | Shared Python package for cross-component code | N/A | Reusable models, utilities | Shared Layer |
| `infra/docker-compose.yml` | Local dev environment definition | N/A | PostgreSQL + MinIO containers | Infrastructure |

### Data Models and Contracts

**Database Schema (Epic 1 Subset)**

```sql
-- accounts table (Jumpstart multi-tenancy pattern)
CREATE TABLE accounts (
    id VARCHAR(255) PRIMARY KEY,  -- Format: acct_abc123
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    credits_balance_micros BIGINT NOT NULL DEFAULT 0,  -- 1 EUR = 1,000,000 micros
    status VARCHAR(50) NOT NULL DEFAULT 'active'  -- active, suspended, deleted
);

-- users table (individual humans, Clerk-synced)
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,  -- Format: user_abc123 (Clerk user ID)
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    clerk_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- account_memberships table (many-to-many join)
CREATE TABLE account_memberships (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(255) NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',  -- owner, admin, member
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, user_id)
);

-- api_keys table (CLI authentication)
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) NOT NULL UNIQUE,  -- bcrypt hash of sk_live_...
    account_id VARCHAR(255) NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name VARCHAR(255),  -- Optional friendly name
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    INDEX idx_account_id (account_id),
    INDEX idx_key_hash (key_hash)
);
```

**Pydantic Models (API Contracts)**

```python
# api/schemas/auth.py
from pydantic import BaseModel, Field
from datetime import datetime

class AuthValidateResponse(BaseModel):
    """Response for POST /api/v1/auth/validate"""
    account_id: str = Field(..., description="Account ID (acct_...)")
    email: str = Field(..., description="Account email")
    credits_balance_micros: int = Field(..., description="Credits in micros")

class HealthResponse(BaseModel):
    """Response for GET /health"""
    status: str = Field(..., description="healthy or degraded")
    database: str = Field(..., description="connected or disconnected")
    storage: str = Field(..., description="connected or disconnected")
    version: str = Field(..., description="API version")

class ErrorResponse(BaseModel):
    """Standard error response format"""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(None, description="Additional error context")
```

**Credentials File Format (INI)**

```ini
# ~/.rgrid/credentials (chmod 600)
[default]
api_key = sk_live_1234567890abcdef1234567890abcdef

# Future: Named profiles
[production]
api_key = sk_live_prodkey...

[staging]
api_key = sk_live_stagingkey...
```

### APIs and Interfaces

**HTTP Endpoints**

| Method | Path | Request | Response | Auth Required | Error Codes |
|--------|------|---------|----------|---------------|-------------|
| GET | `/health` | None | `HealthResponse` | No | 503 (service unavailable) |
| POST | `/api/v1/auth/validate` | Header: `Authorization: Bearer sk_live_...` | `AuthValidateResponse` | Yes (validates the key) | 401 (invalid key), 500 (server error) |

**Endpoint Specifications**

```python
# GET /health
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        HealthResponse: System health status
    """
    db_status = "connected" if await check_database() else "disconnected"
    storage_status = "connected" if await check_minio() else "disconnected"
    overall = "healthy" if db_status == "connected" and storage_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        storage=storage_status,
        version="0.1.0"
    )

# POST /api/v1/auth/validate
@router.post("/api/v1/auth/validate", response_model=AuthValidateResponse, tags=["Authentication"])
async def validate_api_key(
    account: Account = Depends(get_authenticated_account)
):
    """
    Validate API key and return account information.

    Used by CLI during `rgrid init` to verify credentials.

    Headers:
        Authorization: Bearer sk_live_...

    Returns:
        AuthValidateResponse: Account details

    Raises:
        HTTPException 401: Invalid or revoked API key
    """
    return AuthValidateResponse(
        account_id=account.id,
        email=account.email,
        credits_balance_micros=account.credits_balance_micros
    )
```

**Authentication Dependency**

```python
# api/dependencies.py
async def get_authenticated_account(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Account:
    """
    FastAPI dependency for API key authentication.

    Validates API key from Authorization header and returns associated account.
    Updates last_used_at timestamp on api_keys table.

    Args:
        authorization: Authorization header (format: "Bearer sk_live_...")
        db: Database session

    Returns:
        Account: Authenticated account

    Raises:
        HTTPException 401: Missing, invalid, or revoked API key
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = authorization.replace("Bearer ", "")
    account = await auth_service.validate_key(db, api_key)

    if not account:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return account
```

**CLI Command Interface**

```bash
# rgrid init - Interactive authentication setup
$ rgrid init
Enter your API key (from app.rgrid.dev): [hidden input]
✅ Authentication successful! You're ready to run scripts.

# rgrid --version
$ rgrid --version
rgrid, version 0.1.0

# rgrid --help
$ rgrid --help
Usage: rgrid [OPTIONS] COMMAND [ARGS]...

  RGrid - Run Python scripts remotely with zero infrastructure.

Commands:
  init    Initialize RGrid authentication
  run     Execute a script remotely (Epic 2)
  status  Check execution status (Epic 2)
  logs    View execution logs (Epic 8)
```

### Workflows and Sequencing

**Sequence 1: rgrid init (First-Time Setup)**

```
User                    CLI                     API                     Database
  |                      |                       |                         |
  | rgrid init          |                       |                         |
  |-------------------->|                       |                         |
  |                      |                       |                         |
  |                      | Prompt for API key    |                         |
  |                      |<-------------------   |                         |
  | Enter sk_live_...    |                       |                         |
  |-------------------->|                       |                         |
  |                      |                       |                         |
  |                      | POST /api/v1/auth/validate                       |
  |                      |  Header: Authorization: Bearer sk_live_...      |
  |                      |---------------------->|                         |
  |                      |                       |                         |
  |                      |                       | Hash key (bcrypt)       |
  |                      |                       | Query api_keys table    |
  |                      |                       |------------------------>|
  |                      |                       |                         |
  |                      |                       | Return account          |
  |                      |                       |<------------------------|
  |                      |                       |                         |
  |                      |                       | Update last_used_at     |
  |                      |                       |------------------------>|
  |                      |                       |                         |
  |                      | 200 OK + Account info |                         |
  |                      |<----------------------|                         |
  |                      |                       |                         |
  |                      | Write ~/.rgrid/credentials                      |
  |                      | chmod 600             |                         |
  |                      |                       |                         |
  | ✅ Success message   |                       |                         |
  |<--------------------|                       |                         |
```

**Sequence 2: Authenticated CLI Request (Future Commands)**

```
CLI                     API                     Database
  |                      |                         |
  | Load ~/.rgrid/credentials                      |
  |                      |                         |
  | HTTP Request         |                         |
  | Header: Authorization: Bearer sk_live_...      |
  |--------------------->|                         |
  |                      |                         |
  |                      | get_authenticated_account() dependency
  |                      | Hash + lookup api_keys  |
  |                      |------------------------>|
  |                      |                         |
  |                      | Return account          |
  |                      |<------------------------|
  |                      |                         |
  |                      | Execute route handler   |
  |                      | (account passed as param)|
  |                      |                         |
  | Response (JSON)      |                         |
  |<---------------------|                         |
```

**Sequence 3: Development Environment Startup**

```
Developer                   Docker Compose          Make
    |                            |                    |
    | make setup                 |                    |
    |------------------------------------------------>|
    |                            |                    |
    |                            |  docker compose up |
    |                            |<-------------------|
    |                            |                    |
    |  Start PostgreSQL          |                    |
    |  Start MinIO               |                    |
    |<---------------------------|                    |
    |                            |                    |
    |                            |  Install dependencies (Poetry/uv)
    |                            |                    |
    |                            |  pip install -e common/
    |                            |                    |
    |                            |  pip install -e api/
    |                            |                    |
    |                            |  pip install -e cli/
    |                            |                    |
    |                            |  Setup pre-commit hooks
    |                            |                    |
    | ✅ Environment ready       |                    |
    |<------------------------------------------------|
    |                            |                    |
    | uvicorn api.main:app       |                    |
    |                            |                    |
    | API listening on :8000     |                    |
```

## Non-Functional Requirements

### Performance

- **API Response Time:** `/health` endpoint must respond in < 100ms, `/api/v1/auth/validate` in < 200ms (database lookup + bcrypt comparison)
- **CLI Init Time:** `rgrid init` complete authentication flow in < 30 seconds as per FR2 (target: < 1 minute)
- **Database Connection Pool:** Minimum 5 connections, maximum 20 connections for local dev (production sizing in later epics)
- **Concurrent Requests:** FastAPI must handle at least 10 concurrent authentication requests without degradation (foundation for future scale)

### Security

- **API Key Storage:** Keys MUST be bcrypt-hashed (work factor: 12) before database storage; plaintext keys never persisted
- **Credentials File:** `~/.rgrid/credentials` MUST have chmod 600 permissions (owner read/write only); CLI validates on write
- **API Key Format:** `sk_live_` prefix + 32 cryptographically random characters (using `secrets` module)
- **No Secrets in Git:** .gitignore MUST exclude `~/.rgrid/`, `.env`, `credentials`, any file matching `*secret*` or `*key*`
- **HTTPS Only:** API endpoints accessible only via HTTPS in production (local dev may use HTTP)
- **Rate Limiting:** Not implemented in Epic 1 (Epic 10), but auth endpoints designed to support future rate limiting headers
- **SQL Injection Prevention:** All database queries use SQLAlchemy ORM with parameterized queries; no raw SQL except migrations

### Reliability/Availability

- **Database Migration Safety:** All migrations reversible (up/down scripts); tested on fresh database before commit
- **Graceful Degradation:** If MinIO unavailable, `/health` returns "degraded" but API remains operational
- **Error Recovery:** Failed database connections trigger exponential backoff retry (max 3 attempts over 10 seconds)
- **Startup Validation:** FastAPI lifespan events validate database + MinIO connectivity on startup; fail fast if critical dependencies unavailable
- **Transaction Management:** All database writes wrapped in transactions with automatic rollback on error

### Observability

- **Structured Logging:** All logs in JSON format per architecture.md Decision 12:
  ```json
  {
    "timestamp": "2025-11-15T10:30:45.123Z",
    "level": "INFO",
    "component": "api",
    "message": "API key validated",
    "account_id": "acct_abc123",
    "correlation_id": "req_xyz789"
  }
  ```
- **Log Levels:** DEBUG (development only), INFO (successful operations), WARNING (degraded state), ERROR (failures requiring intervention)
- **Metrics:** Expose `/metrics` endpoint for Prometheus (Epic 8); foundations in place for counter/histogram instrumentation
- **Health Checks:** `/health` endpoint provides database + storage connectivity status for monitoring systems
- **OpenAPI Docs:** Auto-generated at `/docs` (FastAPI Swagger UI) and `/redoc` for API exploration

## Dependencies and Integrations

**Python Dependencies (pyproject.toml)**

### API Service (`api/pyproject.toml`)
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
alembic = "^1.12.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
python-dotenv = "^1.0.0"
bcrypt = "^4.1.0"
boto3 = "^1.29.0"  # MinIO client

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
black = "^23.11.0"
ruff = "^0.1.6"
mypy = "^1.7.0"
pre-commit = "^3.5.0"
```

### CLI Tool (`cli/pyproject.toml`)
```toml
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1.0"
httpx = "^0.25.0"
rich = "^13.7.0"  # Terminal formatting
configparser = "^6.0.0"  # INI file parsing

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.11.0"
ruff = "^0.1.6"
mypy = "^1.7.0"
```

### Common Shared Package (`common/pyproject.toml`)
```toml
[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.5.0"
```

**External Services**

| Service | Version | Purpose | Configuration |
|---------|---------|---------|---------------|
| PostgreSQL | 15+ | Primary database for accounts, api_keys, executions | Docker Compose (local), DATABASE_URL env var |
| MinIO | Latest (RELEASE.2023-11-20) | S3-compatible object storage | Docker Compose (local), MINIO_* env vars |
| Python | 3.11+ | Runtime for all services | pyproject.toml constraint |

**Development Tools**

| Tool | Purpose | Configuration |
|------|---------|---------------|
| Docker Compose | Local dev environment | `infra/docker-compose.yml` |
| Alembic | Database migrations | `api/alembic.ini`, `api/alembic/` |
| pytest | Unit/integration testing | `pyproject.toml` [tool.pytest] |
| black | Code formatting | `pyproject.toml` [tool.black], line-length=100 |
| ruff | Linting | `pyproject.toml` [tool.ruff] |
| mypy | Type checking | `pyproject.toml` [tool.mypy], strict mode |
| pre-commit | Git hooks | `.pre-commit-config.yaml` |

**Integration Points**

- **CLI → API:** HTTP requests via httpx, authentication via Authorization header
- **API → Database:** SQLAlchemy 2.0 async ORM via asyncpg driver
- **API → MinIO:** boto3 client for S3 operations (presigned URLs in Epic 7)
- **Common Package:** Imported by both CLI and API for shared Pydantic models (future)

## Acceptance Criteria (Authoritative)

### AC-1.1: Monorepo Structure (Story 1.1)
1. Directory structure matches architecture specification with api/, orchestrator/, runner/, cli/, console/, website/, common/, infra/, tests/, docs/
2. Root includes pyproject.toml, .gitignore, README.md, Makefile
3. Each Python component has pyproject.toml with dependencies
4. Shared `common/` package is installable via `pip install -e common/`

### AC-1.2: Development Environment (Story 1.2)
5. `make setup` installs all Python dependencies
6. `make setup` configures pre-commit hooks (black, ruff, mypy)
7. `make setup` initializes PostgreSQL and MinIO via Docker Compose
8. `make test` executes all unit tests with >= 80% coverage enforcement
9. `make lint` runs formatting (black), linting (ruff), and type checking (mypy)

### AC-1.3: API Key Authentication (Story 1.3)
10. API keys generated with format `sk_live_` + 32 random characters
11. Keys are bcrypt-hashed before storage in api_keys table
12. FastAPI dependency `get_authenticated_account()` validates keys via Authorization header
13. Account is loaded from database on valid key
14. `last_used_at` timestamp updated on each request
15. Invalid keys return 401 Unauthorized with clear error message
16. Revoked keys are rejected with appropriate error

### AC-1.4: CLI Framework (Story 1.4)
17. `rgrid` command available globally after `pip install -e cli/`
18. `rgrid --version` shows current version
19. `rgrid --help` lists all available commands
20. CLI loads credentials from `~/.rgrid/credentials`
21. CLI sends authenticated requests to API with proper headers
22. Results displayed in user-friendly format (not raw JSON)
23. Errors show actionable messages without stack traces
24. Stub commands exist: init, run, status, logs

### AC-1.5: rgrid init Command (Story 1.5)
25. `rgrid init` prompts for API key with secure input (no echo)
26. CLI validates key by calling `POST /api/v1/auth/validate`
27. On success, writes credentials to `~/.rgrid/credentials` with chmod 600
28. On success, displays confirmation message
29. Execution completes in < 30 seconds
30. Invalid key shows error with help URL (app.rgrid.dev/settings/api-keys)
31. Existing credentials trigger overwrite prompt (y/n)
32. Exit code 0 for success, 1 for failure

### AC-1.6: FastAPI Backend (Story 1.6)
33. Database connection pool initialized with asyncpg
34. MinIO client initialized with boto3
35. App serves on http://localhost:8000
36. `GET /health` returns 200 OK with database, storage, version status
37. `POST /api/v1/auth/validate` returns 200 OK with account info for valid key
38. `POST /api/v1/auth/validate` returns 401 Unauthorized for invalid key
39. Pydantic models used for all requests/responses
40. Database migrations configured with Alembic
41. OpenAPI documentation auto-generated at `/docs`

## Traceability Mapping

| AC # | PRD Requirement | Architecture Decision | Component | Story | Test Idea |
|------|----------------|----------------------|-----------|-------|-----------|
| 1-4 | FR1: Install via package manager | Decision 1: Monorepo | api/, cli/, common/, infra/ | 1.1 | Verify directory structure, test pip install -e |
| 5-9 | N/A (Dev tooling) | Decision 7: LLM-friendly | Makefile, docker-compose.yml | 1.2 | Run make commands, verify hooks trigger |
| 10-16 | FR51-FR53: API key auth | Decision 6: Authentication | api/services/auth_service.py | 1.3 | Unit test key generation, validation, bcrypt |
| 17-24 | FR1: Install via pip | Decision 6: Credentials in ~/.rgrid | cli/rgrid/ | 1.4 | Test CLI installation, credential loading |
| 25-32 | FR2: Auth in < 1 min | Decision 6: API Keys | cli/commands/init.py | 1.5 | Integration test init flow, time execution |
| 33-41 | FR54, FR55: Config | Decision 7: API structure | api/main.py, api/routes/ | 1.6 | Test /health and /auth/validate endpoints |

## Risks, Assumptions, Open Questions

### Risks

**RISK-1: Dependency Management Complexity**
- **Description:** Monorepo with multiple Python packages may cause circular dependency issues
- **Mitigation:** Use `common/` as dependency-free shared package; enforce one-way dependencies (cli/api → common, never reverse)
- **Impact:** Medium
- **Status:** Mitigated by architecture design

**RISK-2: Database Migration Failures**
- **Description:** Alembic migrations could fail during development, blocking progress
- **Mitigation:** Test all migrations on fresh database before commit; maintain up/down scripts; use migration testing in CI
- **Impact:** High (blocks development)
- **Status:** Addressed in Story 1.6 DoD

**RISK-3: bcrypt Performance on API Key Validation**
- **Description:** bcrypt is intentionally slow (security feature), may impact auth endpoint latency
- **Mitigation:** Set work factor to 12 (balance security/performance); consider caching account lookups in future epics
- **Impact:** Low (< 200ms target achievable with work factor 12)
- **Status:** Acceptable for Epic 1

### Assumptions

**ASSUMPTION-1:** Developers have Docker installed and can run Docker Compose for local development
- **If false:** Provide alternative setup instructions for native PostgreSQL/MinIO installation

**ASSUMPTION-2:** Clerk integration for web auth will be straightforward in Epic 10
- **If false:** May need to revisit users table schema or add Clerk-specific fields

**ASSUMPTION-3:** Python 3.11+ is acceptable minimum version
- **If false:** May need to support 3.10 (adjust pyproject.toml, test compatibility)

**ASSUMPTION-4:** API will run on single server initially (no load balancing)
- **If false:** Need to add session affinity or stateless auth (already stateless, so low risk)

### Open Questions

**QUESTION-1:** Should we support API key rotation in Epic 1 or defer to Epic 10?
- **Current decision:** Defer to Epic 10; include revocation but not rotation
- **Rationale:** YAGNI for MVP; rotation adds complexity without immediate value

**QUESTION-2:** What should default PostgreSQL/MinIO credentials be for local dev?
- **Proposed:** postgres/postgres for DB, minioadmin/minioadmin for MinIO (standard defaults)
- **Security note:** Different credentials required for production

**QUESTION-3:** Should CLI have auto-update mechanism?
- **Current decision:** No, manual pip upgrade only for Epic 1
- **Future:** Consider auto-update notification in Epic 10

## Test Strategy Summary

### Test Pyramid

```
           ┌─────────────┐
           │ Integration │  10% - Full CLI → API → DB flows
           └─────────────┘
          ┌──────────────────┐
          │  Service Tests   │  30% - Service layer business logic
          └──────────────────┘
      ┌─────────────────────────┐
      │      Unit Tests         │  60% - Pure functions, models, utilities
      └─────────────────────────┘
```

### Test Levels

**Unit Tests (60% of coverage)**
- **Scope:** Pure functions, Pydantic models, utility functions
- **Tools:** pytest, pytest-asyncio
- **Examples:**
  - Test API key generation format (sk_live_ prefix, 32 chars)
  - Test bcrypt hashing/verification
  - Test Pydantic model validation
  - Test credential file parsing
- **Coverage target:** 80% overall, 90% for auth_service.py

**Service Tests (30% of coverage)**
- **Scope:** Service layer business logic with mocked dependencies
- **Tools:** pytest with mocked database/MinIO
- **Examples:**
  - Test auth_service.validate_key() with mock database
  - Test credential loading with mock filesystem
  - Test health check logic with mocked connections
- **Coverage target:** 80% for all service modules

**Integration Tests (10% of coverage)**
- **Scope:** End-to-end flows across components
- **Tools:** pytest with testcontainers (PostgreSQL + MinIO)
- **Examples:**
  - `rgrid init` full flow: CLI → API → DB → credentials file
  - API key validation full flow: header → dependency → DB lookup → response
  - Health check with real database/MinIO connections
- **Coverage target:** Critical paths only

### Test Frameworks

| Component | Framework | Key Plugins |
|-----------|-----------|-------------|
| API | pytest + pytest-asyncio | pytest-cov, httpx (test client) |
| CLI | pytest | click.testing (CliRunner) |
| Database | pytest + testcontainers | PostgreSQL container for integration tests |
| Coverage | pytest-cov | Enforce 80% minimum via pytest.ini |

### Test Execution

```bash
# Run all tests
make test

# Run with coverage report
pytest --cov=api --cov=cli --cov=common --cov-report=html --cov-report=term

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run specific test file
pytest tests/api/test_auth_service.py
```

### CI/CD Testing Strategy

- **Pre-commit hooks:** Run black, ruff, mypy on changed files
- **PR validation:** Run full test suite + coverage check (blocks merge if < 80%)
- **Main branch:** Run tests + generate coverage badge
- **Nightly:** Run integration tests with production-like environment

### Test Data Management

- **Unit tests:** Use fixture factories (pytest-factoryboy pattern)
- **Integration tests:** Use database seeding scripts in conftest.py
- **API keys:** Generate test keys with known plaintext for validation tests
- **Credentials:** Use temporary directories for filesystem tests (pytest tmp_path fixture)
