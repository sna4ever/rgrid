# Story 7.3: Store Outputs in MinIO with Retention Policy

Status: ready-for-dev

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

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 7.2

### Technical Notes



### References

- [Source: docs/epics.md - Story 7.3]
- [Source: docs/sprint-artifacts/tech-spec-epic-7.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/7-3-store-outputs-in-minio-with-retention-policy.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
