# Story 1.1: Initialize Monorepo Project Structure

Status: ready-for-dev

## Story

As a developer,
I want a properly structured monorepo with all components organized logically,
So that I can develop API, orchestrator, runner, CLI, and web apps in a cohesive codebase.

## Acceptance Criteria

1. Directory structure follows the architecture:
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

2. Root includes: `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`

3. Each Python component has `pyproject.toml` with dependencies

4. Shared `common/` package is installable via `pip install -e common/`

## Tasks / Subtasks

- [ ] Task 1: Create root directory structure (AC: #1, #2)
  - [ ] Create api/, orchestrator/, runner/, cli/, console/, website/, common/, infra/, tests/, docs/ directories
  - [ ] Create root pyproject.toml with monorepo configuration
  - [ ] Create .gitignore excluding venv/, __pycache__/, .env, ~/.rgrid/
  - [ ] Create README.md with project overview
  - [ ] Create Makefile with setup, test, lint, format, clean targets

- [ ] Task 2: Set up Python package structure (AC: #3)
  - [ ] Create api/pyproject.toml with FastAPI dependencies
  - [ ] Create api/app/ with __init__.py, main.py
  - [ ] Create api/app/api/v1/, api/app/services/, api/app/schemas/, api/app/models/ subdirectories
  - [ ] Create orchestrator/pyproject.toml with dependencies
  - [ ] Create runner/pyproject.toml with Docker SDK dependencies
  - [ ] Create cli/pyproject.toml with Click dependencies

- [ ] Task 3: Create shared common package (AC: #4)
  - [ ] Create common/pyproject.toml
  - [ ] Create common/rgrid_common/__init__.py
  - [ ] Create common/rgrid_common/models.py for shared Pydantic models
  - [ ] Create common/rgrid_common/money.py for Money class (MICRONS handling)
  - [ ] Create common/rgrid_common/types.py for shared type definitions
  - [ ] Test pip install -e common/ works correctly

- [ ] Task 4: Set up infrastructure scaffolding (AC: #1)
  - [ ] Create infra/docker-compose.yml (placeholder for Story 1.2)
  - [ ] Create infra/dockerfiles/ directory for custom images
  - [ ] Create infra/terraform/ directory for cloud infrastructure
  - [ ] Create infra/cloud-init/ directory for worker init scripts

- [ ] Task 5: Initialize test structure (AC: #1)
  - [ ] Create tests/unit/ directory
  - [ ] Create tests/integration/ directory
  - [ ] Create tests/conftest.py with pytest configuration
  - [ ] Create tests/__init__.py

## Dev Notes

### Architecture Alignment

**Decision 1: Monorepo Structure** (architecture.md lines 461-540)
- Monorepo enables atomic changes across CLI + API + orchestrator
- Shared type definitions prevent drift between components
- Single CI/CD pipeline simplifies deployment
- Common package provides shared code without circular dependencies

**Key Constraints:**
- One-way dependencies: cli/api/orchestrator → common (never reverse)
- Each component is independently testable
- Shared common/ package has zero external dependencies for maximum portability

**Directory Structure Rationale:**
```
rgrid/
├── pyproject.toml              # Root config, Poetry workspace
├── rgrid_common/               # Shared package (models, Money, types)
├── cli/                        # Published to PyPI as 'rgrid'
├── api/                        # FastAPI control plane
├── orchestrator/               # Auto-scaler daemon
├── runner/                     # Worker node agent
├── console/                    # Next.js dashboard
├── website/                    # Next.js marketing site
├── infra/                      # IaC and deployment configs
├── tests/                      # Monorepo-wide tests
└── docs/                       # Documentation
```

### LLM-Agent-Friendly Patterns

**Decision 7: LLM-Agent Friendly Code** (architecture.md lines 179-190)
- Stable folder structure - predictable file locations
- Pydantic everywhere - explicit types, auto-validation
- Pure service functions - business logic separate from HTTP handlers
- Explicit SQLAlchemy types - no implicit type coercion
- Comprehensive docstrings - every function documents inputs/outputs
- No magic - explicit imports, no dynamic module loading
- Single responsibility - each module has one clear purpose
- Consistent naming - services/, routes/, schemas/, models/ pattern
- Test-friendly - dependency injection for all external dependencies
- OpenAPI-first - auto-generated docs from Pydantic models

### File Size Constraints

Per architecture.md:
- Single file MUST NOT exceed 500 lines
- If file approaches limit, split by responsibility (e.g., routes/executions.py → routes/executions_create.py, routes/executions_status.py)
- Prefer many small modules over few large files

### Testing Strategy

**TDD Approach** (Tech Spec lines 630-715)
- Write tests BEFORE implementation
- 60% unit tests (pure functions, models)
- 30% service tests (mocked dependencies)
- 10% integration tests (full flows)
- Target: 80% coverage minimum
- Use pytest + pytest-asyncio for all tests

### MICRONS Pattern

**Critical:** All cost tracking uses MICRONS from Day 1 (1 EUR = 1,000,000 micros)
- Never use floats for money calculations
- common/rgrid_common/money.py provides Money class for conversions
- Database stores BIGINT for all cost fields
- Even though billing logic is Epic 9, schema must support it from Epic 1

### Prerequisites

**None** - This is the first story in the project

### References

- [Source: docs/architecture.md - Decision 1: Project Structure (lines 461-540)]
- [Source: docs/architecture.md - Decision 7: LLM-Agent Friendly (lines 179-190)]
- [Source: docs/sprint-artifacts/tech-spec-epic-1.md - AC-1.1 (lines 514-519)]
- [Source: docs/epics.md - Story 1.1 (lines 214-246)]
- [Source: docs/PRD.md - FR1: Install via package manager]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/1-1-initialize-monorepo-project-structure.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
