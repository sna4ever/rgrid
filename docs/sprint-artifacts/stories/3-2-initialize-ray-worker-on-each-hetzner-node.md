# Story 3.2: Initialize Ray Worker on Each Hetzner Node

Status: ready-for-dev

## Story

As developer,
I want each Hetzner worker node to automatically join the Ray cluster on startup,
So that tasks can be distributed to workers.

## Acceptance Criteria

1. Given** a Hetzner worker node is provisioned
2. When** runner initializes
3. Then** Ray worker connects to head node at 10.0.0.1:6379
4. And** Ray worker registers with cluster
5. And** worker is visible in Ray dashboard
6. And** worker advertises max_concurrent = 2 (1 job per vCPU)

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 3.1

### Technical Notes



### References

- [Source: docs/epics.md - Story 3.2]
- [Source: docs/sprint-artifacts/tech-spec-epic-3.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/3-2-initialize-ray-worker-on-each-hetzner-node.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
