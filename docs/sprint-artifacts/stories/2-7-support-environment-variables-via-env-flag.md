# Story 2.7: Support Environment Variables via --env Flag

Status: ready-for-dev

## Story

As developer,
I want to pass environment variables to my script,
So that I can configure behavior without changing code.

## Acceptance Criteria

1. Given** I run `rgrid run script.py --env API_KEY=abc123 --env DEBUG=true`
2. When** execution starts
3. Then** runner sets environment variables in container
4. And** script can access via os.environ['API_KEY']

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 2.6

### Technical Notes



### References

- [Source: docs/epics.md - Story 2.7]
- [Source: docs/sprint-artifacts/tech-spec-epic-2.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/2-7-support-environment-variables-via-env-flag.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
