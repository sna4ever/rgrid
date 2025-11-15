# Story 1.5: Implement `rgrid init` Command for First-Time Setup

Status: ready-for-dev

## Story

As developer,
I want `rgrid init` to handle first-time authentication setup,
So that users can authenticate in < 1 minute as per FR2.

## Acceptance Criteria

1. Given** a user runs `rgrid init` for the first time
2. When** the command executes
3. Then** CLI prompts: "Enter your API key (from app.rgrid.dev):"
4. And** user enters key (e.g., `sk_live_abc123...`)
5. And** CLI validates key by calling `POST /api/v1/auth/validate`
6. And** on success, writes to `~/.rgrid/credentials`:

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

Story 1.3, Story 1.4

### Technical Notes



### References

- [Source: docs/epics.md - Story 1.5]
- [Source: docs/sprint-artifacts/tech-spec-epic-1.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/1-5-implement-rgrid-init-command-for-first-time-setup.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
