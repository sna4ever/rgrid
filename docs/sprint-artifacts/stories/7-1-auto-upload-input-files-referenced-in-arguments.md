# Story 7.1: Auto-Upload Input Files Referenced in Arguments

Status: done

## Story

As developer,
I want files mentioned in script arguments automatically uploaded,
So that I don't manually manage uploads.

## Acceptance Criteria

1. Given** I run `rgrid run process.py data.csv config.json`
2. When** CLI detects file arguments
3. Then** CLI uploads data.csv and config.json to MinIO
4. And** runner downloads files into container /work directory
5. And** script receives correct file paths as arguments

## Tasks / Subtasks

- [x] Task 1 (AC: #1, #2, #3): File argument detection and validation
  - [x] Detect file arguments via detect_file_arguments()
  - [x] Validate missing files with validate_file_args()
  - [x] Upload files to MinIO with presigned URLs
  - [x] Show upload progress for large files (>1MB)
- [x] Task 2 (AC: #4, #5): Runner path transformation
  - [x] Runner downloads input files to /work directory
  - [x] map_args_to_container_paths() transforms paths for container

## Dev Notes

### Prerequisites

Epic 2 complete

### Technical Notes

- File detection uses `os.path.exists()` to detect file args
- Flags (args starting with `-`) are never treated as files
- validate_file_args() raises FileNotFoundError for explicit file paths that don't exist
- Large files (>1MB) use streaming upload with tqdm progress bar
- Runner uses `map_args_to_container_paths()` to transform paths to `/work/{filename}`

### References

- [Source: docs/epics.md - Story 7.1]
- [Source: docs/sprint-artifacts/tech-spec-epic-7.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/7-1-auto-upload-input-files-referenced-in-arguments.context.xml

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

- Fixed pre-existing mock issues in test_file_handling.py (httpx.stream vs httpx.Client.get)
- Added validate_file_args() for clear error messages on missing files
- Added upload progress display for large files using upload_file_streaming()
- 11 unit tests in test_file_detection.py
- 10 unit tests in test_file_handling.py
- All 21 file-related tests passing

### File List

- cli/rgrid/utils/file_detection.py - Added validate_file_args() and _looks_like_file_path()
- cli/rgrid/commands/run.py - Integrated validation and upload progress display
- tests/unit/test_file_detection.py - NEW: 11 unit tests for Story 7-1
- tests/unit/test_file_handling.py - Fixed mock issues in download tests
