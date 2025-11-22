# Story 9.4: Implement Cost Estimation for Batch Executions

Status: done

## Story

As developer,
I want cost estimates before running batch jobs,
So that I can make informed decisions.

## Acceptance Criteria

1. Given** I run `rgrid estimate --runtime python:3.11 --batch data/*.csv`
2. When** CLI calculates estimate
3. Then** CLI displays estimated executions, duration, and cost

## Tasks / Subtasks

- [x] Task 1 (AC: #1): Implement cost estimation functions
  - [x] Add estimate_batch_cost() to orchestrator/cost.py
  - [x] Add calculate_median_duration() helper
  - [x] Add DEFAULT_ESTIMATE_DURATION_SECONDS constant
- [x] Task 2 (AC: #2): Implement API estimate endpoint
  - [x] Add /api/v1/estimate endpoint with runtime and files params
  - [x] Query historical executions for median duration
  - [x] Return EstimateResponse with cost breakdown
- [x] Task 3 (AC: #3): Implement CLI estimate command
  - [x] Create cli/rgrid/commands/estimate.py
  - [x] Support --batch glob pattern expansion
  - [x] Support --files numeric count
  - [x] Display formatted cost estimate with assumptions
- [x] Task 4: Write comprehensive unit tests (TDD)
  - [x] Test estimate_batch_cost() - 8 tests
  - [x] Test calculate_median_duration() - 4 tests

## Dev Notes

### Prerequisites

Story 9.3 (rgrid cost command)

### Technical Notes

- Uses median duration (p50) instead of mean to handle outliers
- Falls back to 60s default when no historical data available
- Historical data limited to last 30 days, max 100 executions

### References

- [Source: docs/epics.md - Story 9.4]
- [Source: docs/sprint-artifacts/tech-spec-epic-9.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/9-4-implement-cost-estimation-for-batch-executions.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) via Dev 3 agent

### Debug Log References

None required - straightforward implementation

### Completion Notes List

- Implemented TDD approach: wrote 12 failing tests first, then implemented
- Added estimate_batch_cost() and calculate_median_duration() to orchestrator/cost.py
- Added GET /api/v1/estimate endpoint to api/app/api/v1/cost.py
- Added get_estimate() method to cli/rgrid/api_client.py
- Created cli/rgrid/commands/estimate.py with --batch and --files options
- All 12 new unit tests passing (30 total cost tests passing)

### File List

- orchestrator/cost.py - Added estimation functions
- api/app/api/v1/cost.py - Added estimate endpoint
- cli/rgrid/api_client.py - Added get_estimate() method
- cli/rgrid/commands/estimate.py (NEW) - CLI estimate command
- cli/rgrid/cli.py - Registered estimate command
- tests/unit/test_cost_estimation.py (NEW) - 12 unit tests
