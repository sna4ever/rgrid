# Story 6.1: Implement Script Content Hashing and Cache Lookup

Status: done

## Story

As developer,
I want identical scripts cached to avoid rebuilding images,
So that repeat executions start instantly.

## Acceptance Criteria

1. Given** API receives execution request
2. When** API calculates `script_hash = sha256(script_content)`
3. Then** API checks script_cache table for existing hash
4. And** if cache hit, skips Docker build and uses cached image
5. And** if cache miss, builds new image and stores hash

## Tasks / Subtasks

- [x] Task 1 (AC: #1-2): Implement script content hashing
  - [x] Create calculate_script_hash() function with SHA256
  - [x] Write unit tests (15 tests covering determinism, sensitivity, edge cases)
- [x] Task 2 (AC: #3-5): Implement script cache lookup and storage
  - [x] Create script_cache database table migration
  - [x] Create ScriptCache SQLAlchemy model
  - [x] Implement lookup_script_cache() and store_script_cache() functions
  - [x] Integrate script caching into DockerExecutor.execute_script()

## Dev Notes

### Prerequisites

Epic 2 complete

### Technical Notes



### References

- [Source: docs/epics.md - Story 6.1]
- [Source: docs/sprint-artifacts/tech-spec-epic-6.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/6-1-implement-script-content-hashing-and-cache-lookup.context.xml

### Agent Model Used

claude-sonnet-4-5-20250929 (Dev 2)

### Debug Log References

N/A

### Completion Notes List

- Implemented `calculate_script_hash()` function using SHA256 hashing of raw script content
- Script hash is whitespace-sensitive (unlike dependency hash) because Python indentation matters
- Created `script_cache` database table with composite unique index on (script_hash, runtime)
- Implemented `lookup_script_cache()` and `store_script_cache()` with graceful error handling
- Integrated script caching into DockerExecutor - checks cache before building, stores after building
- Added 15 unit tests covering hash calculation, cache lookup/store, and invalidation scenarios
- All 42 caching-related tests pass (script, dependency, and combined cache tests)

### File List

- runner/runner/cache.py - Added calculate_script_hash, lookup_script_cache, store_script_cache
- runner/runner/executor.py - Integrated script caching into execute_script()
- api/app/models/script_cache.py - New SQLAlchemy model
- api/app/models/__init__.py - Added ScriptCache export
- api/alembic/versions/50e12da834f4_add_script_cache_table_for_story_6_1.py - Migration
- tests/unit/test_unit_script_caching.py - 15 unit tests
