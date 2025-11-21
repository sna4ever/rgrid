# Story 7.3: Store Outputs in MinIO with Retention Policy

Status: done

## Story

As developer,
I want outputs stored with 30-day retention,
So that results are available for download but not forever.

## Acceptance Criteria

1. Given** outputs are uploaded to MinIO
2. When** storage writes files
3. Then** files are stored in MinIO bucket: rgrid-executions
4. And** object lifecycle policy deletes files after 30 days
5. And** artifacts table tracks retention expiry date

## Tasks / Subtasks

- [x] Task 1: Configure MinIO lifecycle policy (AC: #4)
  - [x] Create setup_minio_lifecycle.py script
  - [x] Configure 30-day retention rule for executions/ prefix
  - [x] Add verify command to check policy exists
- [x] Task 2: Track expires_at in artifacts (AC: #5)
  - [x] Add expires_at column to Artifact model
  - [x] Auto-calculate expires_at from created_at + retention_days
  - [x] Add ARTIFACT_RETENTION_DAYS environment variable support
- [x] Task 3: Update API response (AC: #5)
  - [x] Return expires_at in artifact list endpoint
- [x] Task 4: Testing
  - [x] 9 unit tests (all passing)
  - [x] 9 integration tests (all passing)

## Dev Notes

### Prerequisites

Story 7.2 (auto-collect outputs) - DONE

### Technical Notes

- MinIO lifecycle policy uses minio Python SDK
- Artifact model uses __init__ to properly set default expires_at
- Retention days configurable via ARTIFACT_RETENTION_DAYS env var (default: 30)
- API endpoint /executions/{exec_id}/artifacts now returns expires_at field

### References

- [Source: docs/epics.md - Story 7.3]
- [Source: docs/sprint-artifacts/tech-spec-epic-7.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/7-3-store-outputs-in-minio-with-retention-policy.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A

### Completion Notes List

1. Created scripts/setup_minio_lifecycle.py for MinIO lifecycle policy setup
2. Updated api/app/models/artifact.py with proper __init__ for expires_at default
3. Added artifact_retention_days to api/app/config.py
4. Updated api/app/api/v1/executions.py to return expires_at in artifact response
5. Added 9 unit tests in tests/unit/test_unit_retention_policy.py
6. Added 9 integration tests in tests/integration/test_integration_retention_policy.py
7. All 18 tests passing

### File List

- scripts/setup_minio_lifecycle.py (NEW)
- api/app/models/artifact.py (MODIFIED)
- api/app/config.py (MODIFIED)
- api/app/api/v1/executions.py (MODIFIED)
- tests/unit/test_unit_retention_policy.py (NEW)
- tests/integration/test_integration_retention_policy.py (NEW)
