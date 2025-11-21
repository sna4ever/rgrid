# Story 8.6: Track Execution Metadata in Database

Status: done

## Story

As developer,
I want comprehensive execution metadata tracked,
So that I can audit and analyze execution history.

## Acceptance Criteria

1. Given** execution runs
2. When** execution completes
3. Then** database records:
4. execution_id, account_id, script_hash
5. start_time, end_time, duration_seconds
6. status (completed/failed), exit_code
7. worker_id, runtime, cost_micros
8. input_files, output_files (artifact references)

## Tasks / Subtasks

- [x] Task 1: Add metadata fields to database models (AC: #1-8)
  - [x] Add duration_seconds, worker_hostname, execution_metadata to API Execution model
  - [x] Add same fields to Runner Execution model
  - [x] Add fields to ExecutionResponse Pydantic schema
- [x] Task 2: Update runner to populate metadata (AC: #1-8)
  - [x] Track started_at in worker.py for duration calculation
  - [x] Calculate duration_seconds on completion
  - [x] Pass worker_hostname to update_execution_result
  - [x] Build execution_metadata with runtime info
- [x] Task 3: Update status command display (AC: #6)
  - [x] Display worker_hostname when available
- [x] Task 4: Write comprehensive unit tests
  - [x] Test model fields exist
  - [x] Test schema serialization
  - [x] Test poller accepts new parameters
  - [x] Test status command displays metadata

## Dev Notes

### Prerequisites

Epic 2 complete

### Technical Notes



### References

- [Source: docs/epics.md - Story 8.6]
- [Source: docs/sprint-artifacts/tech-spec-epic-8.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/8-6-track-execution-metadata-in-database.context.xml

### Agent Model Used

Claude Sonnet 4.5 (Dev 3)

### Debug Log References

N/A - implementation complete

### Completion Notes List

- Added duration_seconds, worker_hostname, execution_metadata fields to Execution models
- Updated poller.update_execution_result() to accept new metadata parameters
- Worker now calculates duration and populates metadata on execution completion
- Status command displays worker_hostname when available
- 22 unit tests written covering all acceptance criteria
- All tests pass (32/33 with 1 pre-existing failure from Story 8-3)

### File List

- api/app/models/execution.py - Added metadata fields
- runner/runner/models.py - Added metadata fields
- common/rgrid_common/models.py - Added fields to ExecutionResponse schema
- runner/runner/poller.py - Updated update_execution_result() parameters
- runner/runner/worker.py - Calculate and store metadata on completion
- cli/rgrid/commands/status.py - Display worker_hostname
- tests/unit/test_execution_metadata.py - New: 22 unit tests for Story 8.6
