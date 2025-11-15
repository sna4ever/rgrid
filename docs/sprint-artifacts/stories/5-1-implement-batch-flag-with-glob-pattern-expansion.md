# Story 5.1: Implement --batch Flag with Glob Pattern Expansion

Status: ready-for-dev

## Story

As developer,
I want to run `rgrid run script.py --batch data/*.csv`,
So that each CSV file creates a separate execution.

## Acceptance Criteria

1. Given** I run `rgrid run process.py --batch inputs/*.csv`
2. When** CLI expands glob pattern
3. Then** CLI finds all matching files (e.g., input1.csv, input2.csv, input3.csv)
4. And** CLI creates N execution requests (one per file)
5. And** each execution receives one input file as argument
6. And** CLI displays: "Starting batch: 3 files, 10 parallel"

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

- [Source: docs/epics.md - Story 5.1]
- [Source: docs/sprint-artifacts/tech-spec-epic-5.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/5-1-implement-batch-flag-with-glob-pattern-expansion.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
