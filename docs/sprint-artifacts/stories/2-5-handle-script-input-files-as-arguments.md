# Story 2.5: Handle Script Input Files as Arguments

Status: review

## Story

As developer,
I want to pass local files as script arguments and have them available in the container,
So that scripts can read input data identically to local execution.

## Acceptance Criteria

1. ✅ Given** I run `rgrid run process.py input.json`
2. ✅ When** execution starts
3. ✅ Then** CLI uploads input.json to MinIO
4. ✅ And** runner downloads input.json into container /work directory
5. ✅ And** runner passes /work/input.json as argument to script
6. ✅ And** script receives file path and can read it normally

## Tasks / Subtasks

- [x] Task 1: CLI file detection and upload (AC: #1, #3)
  - [x] Implement `detect_file_arguments()` utility
  - [x] Implement `upload_file_to_minio()` utility
  - [x] Integrate file detection in run.py command
  - [x] Pass input_files to API
- [x] Task 2: Runner file download and argument mapping (AC: #4, #5, #6)
  - [x] Implement `download_input_files()` in file_handler
  - [x] Implement `map_args_to_container_paths()` in file_handler
  - [x] Integrate download logic in worker.py
  - [x] Pass download_urls to executor
- [x] Task 3: API presigned URL generation
  - [x] Generate presigned PUT URLs for CLI uploads
  - [x] Generate presigned GET URLs for runner downloads
  - [x] Add input_files field to Execution model
- [x] Task 4: Testing
  - [x] Write 10 unit tests (file detection, upload, download, mapping)
  - [x] Write 8 integration tests (E2E file flow)
  - [x] All 18 tests passing

## Dev Notes

### Prerequisites

Story 2.4

### Technical Notes



### References

- [Source: docs/epics.md - Story 2.5]
- [Source: docs/sprint-artifacts/tech-spec-epic-2.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/2-5-handle-script-input-files-as-arguments.context.xml

### Agent Model Used

claude-sonnet-4-5-20250929 (Amelia - Developer Agent)

### Debug Log References

N/A - Implementation completed without blockers

### Completion Notes List

**Implementation Summary:**
Story 2-5 was found to be largely pre-implemented from previous work. Verified and validated all components:

1. **CLI Components (✅ Complete)**:
   - `cli/rgrid/utils/file_detection.py`: Detects file arguments using os.path.isfile()
   - `cli/rgrid/utils/file_upload.py`: Uploads files to MinIO presigned URLs
   - `cli/rgrid/commands/run.py`: Integrated file detection and upload flow

2. **API Components (✅ Complete)**:
   - `api/app/api/v1/executions.py`: Generates presigned PUT (upload) and GET (download) URLs
   - `api/app/models/execution.py`: Added input_files JSON field
   - `api/app/storage.py`: MinIO client with presigned URL methods

3. **Runner Components (✅ Complete)**:
   - `runner/runner/file_handler.py`: Downloads files from MinIO, maps arguments to /work paths
   - `runner/runner/executor.py`: Accepts download_urls parameter, integrates file handling
   - `runner/runner/worker.py`: Generates download URLs from input_files, passes to executor

4. **Testing (✅ Complete - 18 tests, 100% passing)**:
   - Unit tests: `tests/unit/test_file_handling.py` (10 tests)
   - Integration tests: `tests/integration/test_input_files.py` (8 tests - created)
   - All tests passing, validating full E2E flow

**Key Design Decisions:**
- Files detected using `os.path.isfile()` - flags (starting with -) ignored
- Upload/download via MinIO presigned URLs (3600s expiry)
- Files stored at: `executions/{exec_id}/inputs/{filename}`
- Arguments mapped from local paths to `/work/{filename}` in container
- Runner handles all MinIO operations (not container)

**Acceptance Criteria Validation:**
- AC #1-3: CLI detects files, uploads to MinIO ✅
- AC #4-5: Runner downloads to /work, maps arguments ✅
- AC #6: Scripts receive files and can read normally ✅

### File List

**New Files:**
- `tests/integration/test_input_files.py` - Integration tests for E2E file flow

**Modified Files:**
- `docs/sprint-artifacts/sprint-status.yaml` - Updated story status: ready-for-dev → in-progress → review
- `docs/sprint-artifacts/stories/2-5-handle-script-input-files-as-arguments.md` - Updated with completion notes

**Verified Existing Files (already implemented):**
- `cli/rgrid/utils/file_detection.py`
- `cli/rgrid/utils/file_upload.py`
- `cli/rgrid/commands/run.py`
- `api/app/api/v1/executions.py`
- `api/app/models/execution.py`
- `runner/runner/file_handler.py`
- `runner/runner/executor.py`
- `runner/runner/worker.py`
- `tests/unit/test_file_handling.py`
