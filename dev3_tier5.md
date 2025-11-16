# Dev 3 - Tier 5 Wave 3 - Story 6-3

## Git Setup (Run First)

```bash
cd /home/sune/Projects/rgrid
git checkout main
git pull origin main
git checkout -b story-6-3-cache-invalidation
```

## Task

Activate DEV (Amelia). Implement Story 6-3: Implement Automatic Cache Invalidation.

## Story Details

**Epic**: Epic 6 - Caching & Optimization
**Priority**: Critical
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (implicit invalidation via hash change)

## Objective

Stale cache causes wrong results (data corruption!). Ensure cache automatically invalidates when script or dependencies change.

## Acceptance Criteria

- [ ] New hash calculated on every execution (script + deps)
- [ ] Cache lookup fails automatically if hash doesn't match
- [ ] New Docker image built with new hash
- [ ] Old cache entries remain in database (for historical re-runs)
- [ ] No manual cache clearing needed by users
- [ ] Invalidation tested for all scenarios:
  - Script content changes (even 1 character)
  - Requirements.txt changes (add/remove/modify deps)
  - Runtime changes (python → node)
  - Input files changes (for input file caching)
- [ ] Cache hit/miss logged for observability
- [ ] Documentation explains invalidation behavior with examples

## Success Metric

Change 1 line in script - cache miss, new build, new hash. Revert change - cache hit (original hash).

## Files to Modify

- `runner/runner/cache.py` - Enhance hash calculation logic
- `cli/rgrid/commands/run.py` - Log cache hit/miss
- `tests/unit/test_cache_invalidation.py` - NEW FILE - Comprehensive tests
- `tests/integration/test_invalidation_scenarios.py` - NEW FILE - Integration tests
- `docs/caching-behavior.md` - NEW FILE - User documentation

## Testing Strategy (TDD)

**Unit Tests** (tests/unit/test_cache_invalidation.py):
1. `test_script_content_change_invalidates()` - Modify script → new hash
2. `test_deps_change_invalidates()` - Modify requirements.txt → new hash
3. `test_runtime_change_invalidates()` - python → node → new hash
4. `test_cache_hit_after_revert()` - Revert change → original hash → cache hit
5. `test_old_cache_entries_preserved()` - Previous hashes still in DB

**Integration Tests** (tests/integration/test_invalidation_scenarios.py):
1. `test_modify_script_rebuilds()` - End-to-end: change script, verify rebuild
2. `test_add_dependency_rebuilds()` - Add numpy to requirements.txt, verify rebuild
3. `test_remove_dependency_rebuilds()` - Remove numpy, verify rebuild
4. `test_multiple_versions_cached()` - v1, v2, v1 again → 2 cache entries

**Cache Invalidation Matrix** (critical - 2-3 days dedicated testing per TIER5_PLAN):
1. `test_1_char_script_change()` - Single character change invalidates
2. `test_whitespace_change()` - Whitespace-only change invalidates (no normalization)
3. `test_comment_change()` - Comment change invalidates (includes all content)
4. `test_dependency_version_bump()` - numpy==1.20 → numpy==1.21
5. `test_dependency_reorder()` - Reorder lines in requirements.txt (should invalidate)
6. `test_runtime_version_change()` - python:3.11 → python:3.12

**Expected Test Count**: 5 unit tests, 4 integration tests, 6 cache invalidation matrix tests

## Implementation Hints

Enhanced hash calculation:
```python
def calculate_combined_hash(script_content, requirements_content, runtime):
    """
    Calculate combined hash for complete cache key.

    Any change to script, deps, or runtime invalidates cache.
    """
    combined = f"{script_content}\n---\n{requirements_content}\n---\n{runtime}"
    return hashlib.sha256(combined.encode()).hexdigest()
```

Cache lookup with logging:
```python
def lookup_cache(combined_hash):
    result = db.query(ScriptCache).filter_by(script_hash=combined_hash).first()

    if result:
        logger.info(f"Cache HIT: {combined_hash[:8]}")
        return result.docker_image_tag
    else:
        logger.info(f"Cache MISS: {combined_hash[:8]}")
        return None
```

Observability:
```python
# Track cache hit rate
cache_hits = 0
cache_misses = 0

def record_cache_result(hit: bool):
    global cache_hits, cache_misses
    if hit:
        cache_hits += 1
    else:
        cache_misses += 1

    hit_rate = cache_hits / (cache_hits + cache_misses) * 100
    logger.info(f"Cache hit rate: {hit_rate:.1f}%")
```

## Story File

`docs/sprint-artifacts/stories/6-3-cache-invalidation.md`

## Dependencies

✅ Story 6-1 complete (Script content hashing)
✅ Story 6-2 complete (Dependency layer caching from Wave 2)
✅ Story 2-4 complete (Dependency auto-detection)

## Estimated Effort

4-6 hours (plus 2-3 days dedicated cache invalidation testing per TIER5_PLAN)

## Critical Notes

**IMPORTANT**: Cache invalidation bugs cause data corruption (wrong results). This story requires:
- Comprehensive test matrix (15+ test cases)
- All edge cases covered
- Observability instrumented (hit rate logging)
- User documentation with examples

**From TIER5_PLAN Risk Assessment**:
> Cache invalidation bugs: High likelihood, Critical impact
> Mitigation: 2-3 day dedicated testing period, all scenarios tested

**This is the MOST CRITICAL story for data integrity.** Take time to get it right.

---

**Use TDD - write failing tests FIRST, then implement. Test coverage must be 100% for invalidation logic.**

---

## 🎯 REQUIRED: Story Completion Workflow

When development is complete, you MUST follow these steps:

### 1. Update Sprint Status

Edit `docs/sprint-artifacts/sprint-status.yaml`:
- Find your story line
- Change status from `in-progress` → `done`
- Add completion comment

Example:
```yaml
6-3-implement-automatic-cache-invalidation: done  # Tier 5 - Dev 3 - COMPLETED 2025-11-16
```

### 2. Commit Your Work

```bash
git add .
git commit -m "Implement Story X-Y: [Story Title]

- All acceptance criteria met
- Unit tests passing (X tests)
- Integration tests passing (Y tests)
- No regressions

🤖 Generated with Claude Code"
```

### 3. Merge to Main

```bash
git checkout main
git pull origin main
git merge [your-branch-name]
```

### 4. Push to Remote

```bash
git push origin main
```

### 5. Confirm Completion

Reply to user: **"Story X-Y merged and complete"**

---

**⚠️ CRITICAL**: Do NOT say "ready for review" or "ask me anything" without completing these steps first. The story is NOT done until it's merged to main.
