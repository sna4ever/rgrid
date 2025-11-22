# Story 10.4: Implement Structured Error Handling with Clear Messages

Status: done

## Story

As developer,
I want actionable error messages (not stack traces),
So that I can fix issues quickly.

## Acceptance Criteria

1. **Given** execution fails
2. **When** CLI displays error
3. **Then** shows clear, actionable message with:
   - Error type and description
   - Context (execution ID, file path, etc.)
   - Actionable suggestions to fix the issue
   - Command to view logs

## Tasks / Subtasks

- [x] Task 1: Move error classes to shared package (rgrid_common)
  - [x] Create common/rgrid_common/errors.py with all error types
  - [x] Update CLI errors.py to import from rgrid_common
- [x] Task 2: Add error pattern detection
  - [x] Implement detect_error_pattern() for common Python errors
  - [x] Support ModuleNotFoundError, SyntaxError, FileNotFoundError, etc.
- [x] Task 3: Create structured error helpers
  - [x] create_execution_error() with pattern-based suggestions
  - [x] create_validation_error() for input validation
  - [x] format_failed_execution() for displaying failures
- [x] Task 4: Update run command
  - [x] Use structured errors for script read failures
  - [x] Use structured errors for env var validation
  - [x] Use structured errors for file validation
  - [x] Use structured errors for execution failures
- [x] Task 5: Enable and pass all tests
  - [x] Remove skip annotation from test_error_handling.py
  - [x] Add tests for pattern detection
  - [x] Add tests for error creation helpers

## Dev Notes

### Prerequisites

Epic 2 (execution) - Completed

### Technical Notes

Implemented a 3-layer error handling system:
1. **Error Classes** (rgrid_common/errors.py): RGridError, ValidationError, ExecutionError, etc.
2. **Error Detection** (cli/rgrid/errors.py): Pattern matching for common Python errors
3. **CLI Integration** (cli/rgrid/commands/run.py): Structured error display with suggestions

### References

- [Source: docs/epics.md - Story 10.4]
- [Source: docs/sprint-artifacts/tech-spec-epic-10.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/10-4-implement-structured-error-handling-with-clear-messages.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Implementation was straightforward

### Completion Notes List

1. Moved error classes from api/api/errors.py to common/rgrid_common/errors.py for shared access
2. Renamed TimeoutError to RGridTimeoutError to avoid shadowing Python's built-in
3. Added error pattern detection with regex matching for 12+ common error types
4. Implemented context-aware suggestions (e.g., "Add 'pandas' to requirements.txt")
5. Updated run command to use structured errors for all failure scenarios
6. All 23 unit tests passing

### File List

- common/rgrid_common/errors.py (new) - Structured error classes
- cli/rgrid/errors.py (modified) - Error display and pattern detection
- cli/rgrid/commands/run.py (modified) - Structured error integration
- tests/unit/test_error_handling.py (modified) - Enabled tests + new tests

### Example Output

```
❌ Execution Error: Missing Python module: pandas

   Context:
   - execution_id: exec_abc123
   - exit_code: 1
   - missing_module: pandas

💡 Suggestions:
   - Add 'pandas' to requirements.txt
   - Use --runtime python:3.11-datascience for data science packages
   - Use --runtime python:3.11-llm for AI/LLM packages

View full logs: rgrid logs exec_abc123
```
