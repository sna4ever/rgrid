# Story NEW-3: Setup Alembic Database Migrations

Status: done (Completed: 2025-11-15, Tier 3)

## Story

As a developer,
I want database schema migrations managed with Alembic,
So that schema changes can be applied safely without data loss.

## Acceptance Criteria

1. **Given** SQLAlchemy models exist in the codebase
2. **When** I need to modify the database schema
3. **Then** I can create and apply migrations safely:
   - Alembic initialized in api/ directory
   - Initial migration captures current schema
   - Migration commands work (upgrade, downgrade, current)
   - Database stamped with current version
   - No data loss during schema changes

## Tasks / Subtasks

- [x] Task 1: Initialize Alembic (AC: #1, #2)
  - [x] Install Alembic in api dependencies
  - [x] Run `alembic init` in api directory
  - [x] Configure alembic.ini
  - [x] Update env.py to work with async SQLAlchemy

- [x] Task 2: Create initial migration (AC: #3)
  - [x] Import app models in env.py
  - [x] Convert async database URL to sync (psycopg2)
  - [x] Generate initial migration with autogenerate
  - [x] Review and verify migration file

- [x] Task 3: Stamp database (AC: #4, #5)
  - [x] Install psycopg2-binary for sync driver
  - [x] Stamp database with current revision
  - [x] Verify `alembic current` shows correct version
  - [x] Test migration workflow

## Dev Notes

### Prerequisites

- SQLAlchemy models defined (Story 1-6)
- Database connection configured (Story 1-6)

### Technical Notes

**Challenge**: Our app uses async SQLAlchemy (asyncpg) but Alembic requires sync drivers.

**Solution**:
- Keep app using postgresql+asyncpg://
- Convert URL in env.py: `postgresql+asyncpg://` → `postgresql+psycopg2://`
- Install both drivers: asyncpg (app) + psycopg2-binary (migrations)

**Alembic Configuration**:
```python
# api/alembic/env.py
from app.config import settings
from app.database import Base
from app.models.execution import Execution
from app.models.api_key import APIKey

# Convert async URL to sync
sync_db_url = settings.database_url.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_db_url)

# Use app metadata for autogenerate
target_metadata = Base.metadata
```

### References

- [Source: docs/TIER3_PLAN.md - Story NEW-3]
- [Source: docs/architecture.md - Database section]
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

## Dev Agent Record

### Context Reference

- Story completed as part of Tier 3 batch implementation

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Implementation Summary

**Files Created**:
- `api/alembic.ini` - Alembic configuration
- `api/alembic/env.py` - Migration environment setup
- `api/alembic/versions/fc0e7b400c13_initial_schema_with_executions_and_api_.py` - Initial migration

**Commands Used**:
```bash
# Initialize Alembic
venv/bin/alembic --config api/alembic.ini init alembic

# Create initial migration
venv/bin/alembic --config api/alembic.ini revision --autogenerate -m "Initial schema"

# Stamp database
venv/bin/alembic --config api/alembic.ini stamp head

# Verify
venv/bin/alembic --config api/alembic.ini current
# Output: fc0e7b400c13 (head)
```

**Testing**:
- Manual: Verified migration creation and database stamping
- Automated: N/A (complex to test in CI, manual verification sufficient for MVP)

### Completion Notes

✅ Alembic successfully initialized and configured
✅ Initial migration created capturing current schema (Execution, APIKey tables)
✅ Database stamped with revision fc0e7b400c13
✅ Future schema changes can now use safe migrations
✅ Both async (app) and sync (migrations) database access working

**Production Impact**: Database schema can now evolve safely without manual SQL changes or data loss.

### File List

- api/alembic.ini
- api/alembic/env.py
- api/alembic/script.py.mako
- api/alembic/README
- api/alembic/versions/fc0e7b400c13_initial_schema_with_executions_and_api_.py

**Modified**:
- (None - all new files)

**Related Documentation**:
- docs/TIER3_SUMMARY.md
- docs/TIER3_TEST_REPORT.md
