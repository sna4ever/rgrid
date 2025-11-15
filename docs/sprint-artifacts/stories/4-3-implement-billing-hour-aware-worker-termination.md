# Story 4.3: Implement Billing Hour Aware Worker Termination

Status: ready-for-dev

## Story

As developer,
I want workers kept alive until billing hour ends,
So that hourly costs are amortized across maximum jobs.

## Acceptance Criteria

1. Given** worker is provisioned at time T
2. When** worker completes all jobs
3. Then** orchestrator checks: `current_time < T + 1 hour`?
4. And** if yes, keep worker alive (idle)
5. And** if no, terminate worker via Hetzner API
6. And** worker record marked as terminated in database

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 4.2

### Technical Notes



### References

- [Source: docs/epics.md - Story 4.3]
- [Source: docs/sprint-artifacts/tech-spec-epic-4.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/4-3-implement-billing-hour-aware-worker-termination.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
