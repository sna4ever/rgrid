# Story 5.1: Implement --batch Flag with Glob Pattern Expansion

Status: done

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

- [x] Task 1: Implement batch.py module (AC: #2, #3)
  - [x] expand_glob_pattern() function
  - [x] generate_batch_id() function
  - [x] BatchSubmitter class
- [x] Task 2: Update --batch CLI flag (AC: #1, #4, #5, #6)
  - [x] Change from multiple files to glob pattern
  - [x] Integrate BatchSubmitter into run command
- [x] Task 3: Unit tests (9 tests)
- [x] Task 4: Integration tests (5 tests)
- [x] Task 5: Update existing test that used old API

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

- Implemented glob pattern expansion for --batch flag
- Created cli/rgrid/batch.py with expand_glob_pattern(), generate_batch_id(), BatchSubmitter
- Updated cli/rgrid/commands/run.py to use glob pattern instead of multiple files
- 9 unit tests passing (tests/unit/test_batch_glob.py)
- 5 integration tests passing (tests/integration/test_batch_execution.py)
- Updated 1 existing test (test_download_command.py) to use new API

### File List

- cli/rgrid/batch.py (NEW)
- cli/rgrid/commands/run.py (MODIFIED)
- tests/unit/test_batch_glob.py (NEW)
- tests/integration/test_batch_execution.py (NEW)
- tests/integration/test_download_command.py (MODIFIED)
