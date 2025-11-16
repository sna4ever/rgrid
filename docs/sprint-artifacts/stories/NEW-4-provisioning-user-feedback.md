# Story NEW-4: Implement Provisioning User Feedback

Status: ready-for-dev

## Story

As a user,
I want clear feedback during worker provisioning,
So that I understand what's happening during the 60-second wait and can diagnose failures.

## Acceptance Criteria

1. **Given** worker provisioning is triggered
2. **When** provisioning is in progress
3. **Then** CLI displays provisioning status with elapsed time
4. **And** CLI shows spinner/progress during 60-second worker startup
5. **And** Hetzner quota exceeded shows clear error message
6. **And** API failures show retry attempts and error details
7. **And** Network issues show appropriate connectivity error
8. **And** All failure modes are tested

## Tasks / Subtasks

- [ ] Task 1: Implement provisioning status display (AC: #3)
  - [ ] 1.1: Add status message with elapsed timer
  - [ ] 1.2: Implement progress spinner for CLI
- [ ] Task 2: Implement error messages for all failure modes (AC: #5-7)
  - [ ] 2.1: Hetzner quota exceeded error message
  - [ ] 2.2: API failure error with retry counter
  - [ ] 2.3: Network connectivity error message
- [ ] Task 3: Write tests for all failure scenarios (AC: #8)
  - [ ] 3.1: Unit tests for error message formatting
  - [ ] 3.2: Integration tests simulating failure modes

## Dev Notes

### Prerequisites

- Story 4-1 (Hetzner Provisioning) must be complete
- Story 4-2 (Smart Provisioning Algorithm) should be complete

### Technical Notes

**Error Messages Format**:
- Quota exceeded: "Worker limit reached. Upgrade account or wait for workers to free up."
- API failures: "Cloud provider error. Retrying... (attempt 2/3)"
- Network issues: "Cannot reach cloud provider. Check network connection."

**Progress Display**:
- Show: "Provisioning worker... (30s elapsed)"
- Use CLI spinner library (e.g., `rich`, `click.progressbar`, or `yaspin`)

**Implementation Location**:
- CLI: `cli/commands/run.py` or `cli/provisioning_feedback.py`
- Orchestrator: `orchestrator/provisioning.py` (status updates)

### References

- [Source: docs/TIER4_PLAN.md - Story NEW-4]
- [Source: docs/sprint-artifacts/tech-spec-epic-4.md]
- [Source: docs/ARCHITECTURE.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/NEW-4-provisioning-user-feedback.context.xml

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
