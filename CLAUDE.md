# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RGrid is a distributed compute platform for running short-lived, containerized jobs on ephemeral Hetzner CX22 nodes. It provides elastic background compute for tasks like ffmpeg processing, Python scripts, LLM agents, and ETL without managing Kubernetes.

**Core workflow:**
1. Client submits JobSpec (declarative JSON) → API stores in Postgres queue
2. Orchestrator provisions Hetzner nodes on demand based on queue depth
3. Runner on each node claims jobs atomically, downloads inputs, runs Docker containers
4. Outputs uploaded to MinIO S3, artifacts and logs accessible via API
5. Nodes are ephemeral (~60 min lifetime) for cost efficiency

## Architecture

The system consists of five main components:

- **API (FastAPI)**: Validates JobSpec, authenticates via Clerk OIDC, manages Postgres and MinIO
- **Orchestrator**: Async service that autoscales Hetzner nodes based on queue depth, enforces node lifetimes
- **Runner**: Agent process on each worker node that claims jobs, executes Docker containers, handles I/O
- **Storage (MinIO)**: S3-compatible cluster for artifacts and uploaded inputs
- **Database (Postgres)**: Job queue, executions, logs, artifacts, nodes, heartbeats, cost tracking

**Repo structure** (monorepo layout):
- `docs/` - Comprehensive architecture documentation
- `api/` - FastAPI backend
- `orchestrator/` - Autoscaler and node lifecycle daemon
- `runner/` - Worker agent
- `console/` - Next.js frontend
- `cli/` - Python-based rgrid CLI tool
- `infra/` - Terraform, cloud-init templates, Dockerfiles
- `tests/` - Unit and integration tests

## Key Technical Details

**Multi-tenancy**: Clerk-backed auth with accounts → projects → jobs hierarchy

**Queue mechanism**: Postgres-based with `FOR UPDATE SKIP LOCKED` for atomic job claiming

**Job isolation**: Containers run with no network by default, read-only root filesystem, cgroup resource limits

**Compute model**: Hetzner CX22 nodes (2 vCPU) run max 2 concurrent jobs (1 job per vCPU)

**Artifact handling**: Runner (not container) handles all uploads/downloads via MinIO presigned URLs

**JobSpec format**: Kubernetes-inspired declarative spec with runtime/image, command, env, resources, files (inputs/outputs), timeout, network flag

**Reliability**: Automatic retries, dead worker detection via heartbeat timeouts, job timeout enforcement

## Documentation

Full technical documentation in `docs/` directory. Key files:
- `PROJECT_BRIEF.md` - High-level overview
- `ARCHITECTURE.md` - Component descriptions and data flow
- `JOB_SPEC.md` - JobSpec format and examples
- `DB_QUEUE.md` - Database schema and atomic claim pattern
- `REQUIREMENTS.md` - Functional and non-functional requirements
- `DECISIONS.md` - Architecture decision records
- `IMPLEMENTATION_ROADMAP.md` - Development phases

See `docs/TABLE_OF_CONTENTS.md` for complete documentation index.

## Testing Requirements (CRITICAL)

**All code changes MUST include automated tests.** No feature is considered "done" without tests.

### Test-First Workflow (TDD)

When implementing new features or stories:

1. **Write failing tests FIRST**
   - Unit tests for all new functions/classes
   - Integration tests for new features
   - Tests should fail initially (red)

2. **Implement the feature**
   - Write minimal code to make tests pass
   - Tests turn green

3. **Refactor if needed**
   - Tests remain green during refactoring
   - Code quality improves

### Testing Standards

**Unit Tests** (`tests/unit/`):
- Test individual functions/classes in isolation
- Fast execution (< 1 second per test file)
- No external dependencies (mock Docker, DB, etc.)
- Minimum coverage: All public functions

**Integration Tests** (`tests/integration/`):
- Test features end-to-end
- May require Docker, database, etc.
- Reasonable execution time (< 30 seconds per test file)
- Cover critical user workflows

**Test Organization**:
```
tests/
├── unit/
│   ├── test_feature_name.py        # Unit tests for feature
│   └── test_another_feature.py
├── integration/
│   ├── test_e2e_workflow.py        # Integration tests
│   └── test_tier3_features.py
└── conftest.py                     # Shared fixtures
```

### Running Tests

```bash
# Run all tests
venv/bin/pytest tests/ -v

# Run specific test file
venv/bin/pytest tests/unit/test_runtime_resolver.py -v

# Run with coverage
venv/bin/pytest tests/ --cov=api --cov=runner --cov=cli

# Run only fast tests (skip slow integration tests)
venv/bin/pytest tests/ -m "not slow"
```

### Pre-Commit Testing

A pre-commit hook is configured to automatically run tests before allowing commits. If tests fail, the commit will be blocked.

**To bypass** (only in emergencies):
```bash
git commit --no-verify
```

### When Implementing Tiers

When creating TIER_X_PLAN.md, ALWAYS include:

1. **Test Plan Section** (mandatory):
   - List of unit tests to write for each story
   - List of integration tests to write
   - Expected test coverage

2. **Definition of Done** must include:
   - [ ] All unit tests written and passing
   - [ ] All integration tests written and passing
   - [ ] Test coverage report created
   - [ ] Manual testing performed (if applicable)

3. **Test Report** (deliverable):
   - Create TIER_X_TEST_REPORT.md documenting:
     - Tests written
     - Test results
     - Coverage metrics
     - Known gaps

### Test Quality Standards

- **Descriptive names**: `test_timeout_kills_long_running_script()`
- **AAA pattern**: Arrange, Act, Assert
- **Clear assertions**: `assert exit_code == -1, "Timed-out jobs should return -1"`
- **Fixtures**: Use pytest fixtures for setup/teardown
- **Parametrization**: Use `@pytest.mark.parametrize` for multiple scenarios
- **Documentation**: Docstrings explain what the test verifies

### Example Test Structure

```python
"""Unit tests for runtime resolver (Tier 3 - Story 2-3)."""

import pytest
from rgrid_common.runtimes import resolve_runtime


class TestRuntimeResolver:
    """Test the runtime name to Docker image resolver."""

    def test_none_returns_default_runtime(self):
        """When runtime is None, should return default python:3.11."""
        # Arrange
        runtime = None

        # Act
        result = resolve_runtime(runtime)

        # Assert
        assert result == "python:3.11"

    @pytest.mark.parametrize("runtime,expected", [
        ("python", "python:3.11"),
        ("node", "node:20"),
        (None, "python:3.11"),
    ])
    def test_parametrized_resolution(self, runtime, expected):
        """Test multiple runtime resolutions."""
        assert resolve_runtime(runtime) == expected
```

### Current Test Status

- **Total Tests**: 83 passing
- **Unit Tests**: 69 (Tier 1 + Tier 3 runtime resolver)
- **Integration Tests**: 14 (Tier 3 resource limits + timeout)
- **Coverage**: ~80% of implemented features

### Testing Checklist

Before marking any story as "done":

- [ ] Unit tests written for all new functions/classes
- [ ] Integration tests written for new features
- [ ] All tests passing locally
- [ ] Tests added to appropriate test file in tests/
- [ ] Test report updated (if working on a tier)
- [ ] Pre-commit hook runs tests successfully
- [ ] Manual testing performed for UI/UX changes

**Remember**: Tests are not optional. They are a core deliverable, just like code.
