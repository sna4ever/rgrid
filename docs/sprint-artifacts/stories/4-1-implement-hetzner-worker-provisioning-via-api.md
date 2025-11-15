# Story 4.1: Implement Hetzner Worker Provisioning via API

Status: ready-for-dev

## Story

As developer,
I want orchestrator to provision Hetzner workers via API,
So that capacity scales automatically with queue depth.

## Acceptance Criteria

1. Given** orchestrator detects queue depth > 0 and no available workers
2. When** provisioning logic executes
3. Then** orchestrator calls Hetzner API to create CX22 server
4. And** server uses cloud-init script to install Docker, Ray, runner
5. And** worker joins Ray cluster within 60 seconds
6. And** worker record created in workers table

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Epic 3 complete

### Technical Notes



### References

- [Source: docs/epics.md - Story 4.1]
- [Source: docs/sprint-artifacts/tech-spec-epic-4.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/4-1-implement-hetzner-worker-provisioning-via-api.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
