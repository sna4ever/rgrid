# Story 10.6: Implement Manual Retry Command

Status: done

## Story

As developer,
I want to manually retry failed executions,
So that I can fix transient failures.

## Acceptance Criteria

1. **Given** execution failed
2. **When** I run `rgrid retry exec_abc123`
3. **Then** API creates new execution with same script/inputs
4. **And** new execution_id is generated
5. **And** CLI displays: "Retry started: exec_xyz789"

## Tasks / Subtasks

- [x] Task 1: Create CLI retry command
  - [x] Create cli/rgrid/commands/retry.py
  - [x] Add retry command to cli.py
  - [x] Support --force flag for retrying non-failed executions
- [x] Task 2: Add API endpoint
  - [x] POST /api/v1/executions/{execution_id}/retry
  - [x] Copy input files in MinIO to new execution
  - [x] Create new execution record with same parameters
- [x] Task 3: Add API client method
  - [x] retry_execution() method
- [x] Task 4: Add MinIO copy support
  - [x] copy_object() method in storage.py
- [x] Task 5: Write and pass tests
  - [x] 7 unit tests for retry command

## Dev Notes

### Prerequisites

Epic 2 (execution) - Completed

### Technical Notes

Implementation details:
1. **CLI Command**: `rgrid retry <execution_id> [--force]`
   - Fetches original execution to check status
   - Warns if retrying non-failed/completed execution
   - --force bypasses status check
   - Displays new execution ID and status commands

2. **API Endpoint**: `POST /executions/{execution_id}/retry`
   - Fetches original execution from database
   - Copies input files in MinIO to new execution folder
   - Creates new execution record with same script/runtime/args/env/inputs
   - Returns new execution response

3. **MinIO Copy**: Uses S3 copy_object API for efficient file duplication

### References

- [Source: docs/epics.md - Story 10.6]
- [Source: docs/sprint-artifacts/tech-spec-epic-10.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/10-6-implement-manual-retry-command.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A

### Completion Notes List

1. Created cli/rgrid/commands/retry.py with full retry command
2. Added retry_execution() method to API client
3. Added POST /executions/{id}/retry endpoint
4. Added copy_object() to MinIO client for file copying
5. All 7 unit tests passing

### File List

- cli/rgrid/commands/retry.py (new) - Retry CLI command
- cli/rgrid/cli.py (modified) - Register retry command
- cli/rgrid/api_client.py (modified) - Add retry_execution method
- api/app/api/v1/executions.py (modified) - Add retry endpoint
- api/app/storage.py (modified) - Add copy_object method
- tests/unit/test_retry_command.py (new) - Unit tests

### Example Usage

```bash
# Retry a failed execution
$ rgrid retry exec_abc123
Retry started: exec_xyz789
Original: exec_abc123
Status: queued

Check status: rgrid status exec_xyz789
View logs: rgrid logs exec_xyz789

# Force retry a running execution
$ rgrid retry exec_abc123 --force
```
