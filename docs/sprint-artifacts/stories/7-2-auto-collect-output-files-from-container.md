# Story 7.2: Auto-Collect Output Files from Container

Status: ready-for-dev

## Story

As developer,
I want all files created in /work directory automatically collected,
So that outputs are captured without explicit specification.

## Acceptance Criteria

1. Given** script creates files in working directory
2. When** execution completes
3. Then** runner scans /work for all files
4. And** runner uploads all outputs to MinIO: executions/<exec_id>/outputs/
5. And** artifacts recorded in database with metadata

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 7.1

### Technical Notes



### References

- [Source: docs/epics.md - Story 7.2]
- [Source: docs/sprint-artifacts/tech-spec-epic-7.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/7-2-auto-collect-output-files-from-container.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
