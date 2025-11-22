# Story 5.6: Implement Retry for Failed Batch Executions

Status: done

## Story

As developer,
I want to retry only failed executions from a batch,
So that I don't re-run successful ones.

## Acceptance Criteria

1. Given** batch execution completed with some failures
2. When** I run `rgrid retry --batch <batch-id> --failed-only`
3. Then** CLI retries only executions with status = failed
4. And** successful executions are skipped
5. And** retried executions get new execution IDs

## Tasks / Subtasks

- [x] Task 1 (AC: #1, #2): Add --batch and --failed-only options to retry command
  - [x] Subtask 1.1: Modify retry.py to accept --batch option
  - [x] Subtask 1.2: Add --failed-only flag for filtering
- [x] Task 2 (AC: #3, #4, #5): Implement batch retry logic
  - [x] Subtask 2.1: Fetch batch executions via get_batch_executions()
  - [x] Subtask 2.2: Filter by status=failed when --failed-only is set
  - [x] Subtask 2.3: Retry each filtered execution with retry_execution()
  - [x] Subtask 2.4: Display summary with new execution IDs
- [x] Task 3: Write unit tests
  - [x] Subtask 3.1: Test --failed-only filters correctly
  - [x] Subtask 3.2: Test without --failed-only retries all
  - [x] Subtask 3.3: Test error handling and edge cases

## Dev Notes

### Prerequisites

Story 5.5

### Technical Notes

Implementation uses existing API client methods:
- `get_batch_executions(batch_id)` - fetches all executions in batch
- `retry_execution(execution_id)` - creates new execution from original

No new API endpoints required - all functionality built on existing infrastructure.

### References

- [Source: docs/epics.md - Story 5.6]
- [Source: docs/sprint-artifacts/tech-spec-epic-5.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/5-6-implement-retry-for-failed-batch-executions.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Implementation was straightforward

### Completion Notes List

- Added `--batch` (`-b`) option to specify batch ID
- Added `--failed-only` flag to filter to failed executions only
- Refactored retry command into `_retry_batch()` and `_retry_single()` functions
- Batch retry displays rich table with original/new execution IDs
- Handles partial failures gracefully (continues retrying, reports failures)
- Validates mutual exclusivity of execution_id and --batch
- 12 unit tests covering all acceptance criteria

### File List

- `cli/rgrid/commands/retry.py` - Modified: added batch retry support
- `tests/unit/test_batch_retry.py` - New: 12 unit tests for batch retry
