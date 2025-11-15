# Story 2.6: Collect and Store Script Outputs

Status: ready-for-dev

## Story

As developer,
I want all files created by my script automatically collected and stored,
So that I can retrieve results after execution completes.

## Acceptance Criteria

1. Given** a script creates output files in working directory
2. When** script execution completes
3. Then** runner scans /work directory for all files created
4. And** runner uploads all outputs to MinIO: executions/<exec_id>/outputs/
5. And** runner records artifacts in database: artifacts table
6. And** CLI can download outputs via `rgrid download <exec_id>`

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 2.5

### Technical Notes



### References

- [Source: docs/epics.md - Story 2.6]
- [Source: docs/sprint-artifacts/tech-spec-epic-2.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/2-6-collect-and-store-script-outputs.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
