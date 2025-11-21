# Story 6.2: Implement Dependency Layer Caching

Status: done

## Story

As developer,
I want requirements.txt changes to trigger rebuild while identical deps use cache,
So that dependency installations are fast.

## Acceptance Criteria

1. Given** script has requirements.txt
2. When** API calculates `deps_hash = sha256(requirements_content)`
3. Then** API checks dependency_cache table
4. And** if cache hit, uses cached pip layer
5. And** if cache miss, runs `pip install -r requirements.txt` and caches layer

## Tasks / Subtasks

- [x] Task 1 (AC: #1-2): Implement dependency hash calculation
  - [x] Create calculate_deps_hash() with normalization (sort lines, strip whitespace)
  - [x] Write unit tests for hash calculation (4 tests)
- [x] Task 2 (AC: #3-5): Implement cache lookup and storage
  - [x] Create dependency_cache database table migration
  - [x] Implement lookup_dependency_cache() and store_dependency_cache()
  - [x] Write unit tests for cache functions (7 tests)
- [x] Task 3: Integrate into executor
  - [x] Integrate caching in build_image_with_dependencies()

## Dev Notes

### Prerequisites

Story 6.1

### Technical Notes



### References

- [Source: docs/epics.md - Story 6.2]
- [Source: docs/sprint-artifacts/tech-spec-epic-6.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/6-2-implement-dependency-layer-caching.context.xml

### Agent Model Used

claude-sonnet-4-5-20250929 (Dev 2) - Verification only (implementation pre-existed)

### Debug Log References

N/A

### Completion Notes List

- Story 6-2 was pre-implemented as part of earlier development
- `calculate_deps_hash()` normalizes requirements.txt (sorts lines, strips whitespace) for consistent hashing
- Unlike script hash, dependency hash is order-independent (same deps in different order = same hash)
- `lookup_dependency_cache()` returns cached Docker image tag on hit, None on miss
- `store_dependency_cache()` uses upsert (ON CONFLICT DO NOTHING) for race condition safety
- `build_image_with_dependencies()` uses BuildKit for efficient layer caching
- All 11 unit tests pass

### File List

- runner/runner/cache.py - calculate_deps_hash, lookup_dependency_cache, store_dependency_cache (lines 175-227)
- runner/runner/executor.py - build_image_with_dependencies() (lines 31-108)
- api/app/models/dependency_cache.py - DependencyCache SQLAlchemy model
- api/alembic/versions/7bfedafb5ca5_add_dependency_cache_table_for_story_6_2.py - Migration
- tests/unit/test_unit_dependency_caching.py - 11 unit tests
