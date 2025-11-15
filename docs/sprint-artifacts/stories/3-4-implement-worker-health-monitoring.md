# Story 3.4: Implement Worker Health Monitoring

Status: ready-for-dev

## Story

As developer,
I want workers to send heartbeats to detect failures,
So that dead workers are removed and jobs are rescheduled.

## Acceptance Criteria

1. Given** workers are running
2. When** worker sends heartbeat every 30 seconds
3. Then** orchestrator updates worker_heartbeats table with timestamp
4. And** orchestrator marks worker as dead if no heartbeat for 2 minutes
5. And** orphaned tasks are rescheduled to other workers

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 3.3

### Technical Notes



### References

- [Source: docs/epics.md - Story 3.4]
- [Source: docs/sprint-artifacts/tech-spec-epic-3.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/3-4-implement-worker-health-monitoring.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
