# Story 5.4: Organize Batch Outputs by Input Filename

Status: done

## Story

As developer,
I want batch outputs organized in ./outputs/<input-name>/ directories,
So that I can map outputs back to inputs easily.

## Acceptance Criteria

1. **Given** batch execution with 3 input files: data1.csv, data2.csv, data3.csv
2. **When** executions complete
3. **Then** CLI downloads outputs to:
   - ./outputs/data1.csv/output.txt
   - ./outputs/data2.csv/output.txt
   - ./outputs/data3.csv/output.txt

## Tasks / Subtasks

- [x] Task 1 (AC: #1-3): Add API endpoint to get batch executions with input files
  - [x] Create GET /batches/{batch_id}/executions endpoint
  - [x] Return execution data with batch_metadata.input_file
- [x] Task 2: Update CLI to use new endpoint
  - [x] Update get_batch_executions() in api_client.py
- [x] Task 3: Add CLI flags for output customization
  - [x] Add --output-dir flag (default: ./outputs)
  - [x] Add --flat flag for flat output structure
- [x] Task 4: Integrate batch download with run command
  - [x] Call download_batch_outputs after batch completion
- [x] Task 5: Write tests
  - [x] Unit tests for helper functions
  - [x] Integration tests for CLI flags
  - [x] 14 tests pass for batch output functionality

## Dev Notes

### Prerequisites

Story 5-1 (batch flag), Story 5-3 (batch progress tracking)

### Technical Notes

- API endpoint `/api/v1/batches/{batch_id}/executions` returns list of executions with `batch_metadata.input_file`
- CLI flags `--output-dir` and `--flat` control output organization
- Output structure: `<output-dir>/<input-name>/<artifact-path>` (nested) or `<output-dir>/<artifact-filename>` (flat)
- Safe directory name handling removes special characters and handles collisions

### References

- [Source: docs/epics.md - Story 5.4]
- [Source: docs/sprint-artifacts/tech-spec-epic-5.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/5-4-organize-batch-outputs-by-input-filename.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Implementation was straightforward

### Completion Notes List

1. Added new API endpoint `GET /batches/{batch_id}/executions` that returns full execution metadata including input files
2. Updated CLI API client's `get_batch_executions()` to call the new endpoint
3. Added `--output-dir` and `--flat` CLI flags to the run command
4. Integrated `download_batch_outputs()` with the run command after batch completion
5. Fixed existing test to patch new batch download function
6. Added 9 new tests for helper functions and CLI integration
7. All 70 batch-related tests pass

### File List

- api/app/api/v1/executions.py (added get_batch_executions endpoint)
- cli/rgrid/api_client.py (updated get_batch_executions method)
- cli/rgrid/commands/run.py (added --output-dir, --flat flags and batch download integration)
- tests/integration/test_batch_outputs.py (added 9 new tests)
- tests/unit/test_auto_download.py (fixed test to patch download_batch_outputs)
