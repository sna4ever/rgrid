# Story 8.5: Implement Batch Progress Display with --watch

Status: done

## Story

As developer,
I want batch progress displayed with `rgrid run --batch data/*.csv --watch`,
So that I can monitor parallel execution status.

## Acceptance Criteria

1. Given** batch execution with --watch flag
2. When** executions run
3. Then** CLI displays aggregate progress:
   - Visual progress bar
   - Completed/failed/running/queued counts
   - Duration and ETA
   - Total cost in EUR

## Tasks / Subtasks

- [x] Task 1: Add cost to batch status API
  - [x] Update GET /batches/{batch_id}/status to include total_cost_micros
- [x] Task 2: Implement progress display with cost and duration
  - [x] Add format_cost() function
  - [x] Add format_progress_with_cost() function
  - [x] Add format_final_summary_with_cost() function
  - [x] Add calculate_progress_with_cost() function
  - [x] Add display_batch_progress_with_watch() function
- [x] Task 3: Add --watch flag to CLI
  - [x] Add --watch/-w flag to run command
  - [x] Update batch flow to use --watch for progress monitoring

## Dev Notes

### Prerequisites

Story 5.3, Story 8.3

### Technical Notes

The --watch flag enables real-time progress monitoring for batch executions. Without --watch, batch submissions exit immediately with a message to check status later.

Progress display format:
```
[=========>           ] 45/100 (45.0%) (3 failed, 10 running, 42 queued)
Duration: 2m 30s | ETA: 3m 15s | Cost: EUR 0.90
```

### References

- [Source: docs/epics.md - Story 8.5]
- [Source: docs/sprint-artifacts/tech-spec-epic-8.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/8-5-implement-batch-progress-display-with-watch.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

All 27 batch progress unit tests passing including 6 new tests for Story 8-5.

### Completion Notes List

1. Added --watch/-w flag to rgrid run command
2. Enhanced batch status API to return total_cost_micros
3. New progress display functions with cost and duration support
4. Changed default batch behavior: without --watch, batch submissions exit immediately
5. With --watch: Full progress monitoring with cost display, then auto-download outputs

### File List

- cli/rgrid/batch_progress.py (added format_cost, format_progress_with_cost, format_final_summary_with_cost, calculate_progress_with_cost, display_batch_progress_with_watch)
- cli/rgrid/commands/run.py (added --watch flag and updated batch flow)
- api/app/api/v1/executions.py (updated get_batch_status to include total_cost_micros)
- tests/unit/test_unit_batch_progress.py (added TestProgressWithCostAndDuration, TestCalculateProgressWithCost)
