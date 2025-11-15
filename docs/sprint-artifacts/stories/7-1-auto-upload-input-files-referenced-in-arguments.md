# Story 7.1: Auto-Upload Input Files Referenced in Arguments

Status: ready-for-dev

## Story

As developer,
I want files mentioned in script arguments automatically uploaded,
So that I don't manually manage uploads.

## Acceptance Criteria

1. Given** I run `rgrid run process.py data.csv config.json`
2. When** CLI detects file arguments
3. Then** CLI uploads data.csv and config.json to MinIO
4. And** runner downloads files into container /work directory
5. And** script receives correct file paths as arguments

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Epic 2 complete

### Technical Notes



### References

- [Source: docs/epics.md - Story 7.1]
- [Source: docs/sprint-artifacts/tech-spec-epic-7.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/7-1-auto-upload-input-files-referenced-in-arguments.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
