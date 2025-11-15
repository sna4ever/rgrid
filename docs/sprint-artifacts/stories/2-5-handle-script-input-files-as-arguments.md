# Story 2.5: Handle Script Input Files as Arguments

Status: ready-for-dev

## Story

As developer,
I want to pass local files as script arguments and have them available in the container,
So that scripts can read input data identically to local execution.

## Acceptance Criteria

1. Given** I run `rgrid run process.py input.json`
2. When** execution starts
3. Then** CLI uploads input.json to MinIO
4. And** runner downloads input.json into container /work directory
5. And** runner passes /work/input.json as argument to script
6. And** script receives file path and can read it normally

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 2.4

### Technical Notes



### References

- [Source: docs/epics.md - Story 2.5]
- [Source: docs/sprint-artifacts/tech-spec-epic-2.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/2-5-handle-script-input-files-as-arguments.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
