# RGrid Caching Behavior

## Overview

RGrid implements two levels of caching to optimize execution performance while maintaining data integrity:

1. **Dependency Layer Caching** (Story 6-2)
2. **Combined Caching with Automatic Invalidation** (Story 6-3)

## Dependency Layer Caching

**Purpose**: Avoid reinstalling the same Python dependencies repeatedly.

**How it works**:
- When you include a `requirements.txt` file in your script directory, RGrid calculates a hash of the dependencies
- The hash is **normalized** (dependencies are sorted alphabetically) so order doesn't matter
- If the same dependencies have been installed before, RGrid reuses the cached Docker layer
- **First run**: ~60 seconds (install dependencies)
- **Subsequent runs**: ~5 seconds (use cached layer)

**Example**:
```bash
# First run with requirements.txt
$ rgrid run script.py
ℹ Detected requirements.txt with 3 dependencies
  Dependencies will be cached for faster execution
Execution time: 62s (installing numpy, pandas, requests)

# Second run with same requirements.txt
$ rgrid run script.py
ℹ Detected requirements.txt with 3 dependencies
  Dependencies will be cached for faster execution
Execution time: 4s (cached!)
```

## Combined Caching with Automatic Invalidation

**Purpose**: Cache complete execution environments while ensuring cache automatically invalidates on ANY change.

**Critical**: Cache invalidation bugs cause data corruption! RGrid's cache invalidation is intentionally aggressive.

**Hash includes**:
- Script content (every character, including whitespace and comments)
- Requirements.txt content (every character, order-sensitive)
- Runtime (e.g., `python:3.11`)

**Automatic Invalidation Scenarios**:

| Change | Cache Behavior | Example |
|--------|---------------|---------|
| Script content (1 char) | **INVALIDATE** | `print('hello')` → `print('hello!')` |
| Whitespace only | **INVALIDATE** | `print('hi')` → `print('hi') ` (trailing space) |
| Comments | **INVALIDATE** | Add `# Comment` to script |
| Add dependency | **INVALIDATE** | Add `pandas==2.0.0` to requirements.txt |
| Remove dependency | **INVALIDATE** | Remove `numpy==1.24.0` |
| Change version | **INVALIDATE** | `numpy==1.20.0` → `numpy==1.21.0` |
| Reorder dependencies | **INVALIDATE** | Different line order in requirements.txt |
| Change runtime | **INVALIDATE** | `python:3.11` → `python:3.12` |
| Revert to original | **CACHE HIT!** | Change back to original version |

**Example workflow**:
```bash
# Run version 1
$ rgrid run script.py
✗ Cache MISS: abc123de... (building new image)
Execution time: 65s

# Run version 2 (modified script)
$ rgrid run script.py
✗ Cache MISS: xyz789ab... (building new image)
Execution time: 64s

# Revert to version 1 (same as first run)
$ rgrid run script.py
✓ Cache HIT: abc123de... (using cached image)
Execution time: 5s
```

## Why Two Cache Levels?

**Dependency Layer Cache**:
- **Order-independent**: `numpy\npandas` = `pandas\nnumpy` (same hash)
- **Optimized for dependencies**: Reordering doesn't trigger rebuild
- **Shared across scripts**: Multiple scripts can share the same dependency layer

**Combined Cache**:
- **Order-sensitive**: ANY change invalidates (including reorder)
- **Complete environment**: Script + deps + runtime
- **Data integrity**: Prevents stale cache bugs

## Cache Hit Rate Logging

RGrid logs cache performance for observability:

```
Cache HIT: abc123de... (using cached image)
Cache MISS: xyz789ab... (building new image)
```

Monitor these logs to understand your cache hit rate and optimize your workflow.

## Best Practices

1. **Pin dependency versions**: `numpy==1.24.0` (not `numpy`)
   - Ensures reproducible builds
   - Maximizes cache hits

2. **Keep requirements.txt stable**: Don't change unless needed
   - Dependency changes invalidate cache
   - Group dependency updates together

3. **Use version control**: Git helps you revert to cached versions
   - Reverting to a previous commit gives cache hit
   - Historical versions remain cached

4. **Understand invalidation**: Cache invalidates on ANY change
   - Even whitespace changes invalidate
   - This is intentional for data integrity

## FAQ

**Q: Why does whitespace change invalidate cache?**

A: Data integrity. Even small changes can affect execution behavior (e.g., Python indentation). RGrid prioritizes correctness over performance.

**Q: Can I manually clear the cache?**

A: Not needed! Cache invalidation is automatic. Old cache entries are preserved (not deleted) so reverting code gives cache hits.

**Q: How much disk space does caching use?**

A: Each unique combination of (script + deps + runtime) creates one cached Docker image (~500MB-1GB each). Monitor disk usage and periodically prune old images if needed.

**Q: Does cache work across different projects?**

A: Yes! If two projects use identical script + deps + runtime, they share the same cache entry. This is why we use content-based hashing instead of file paths.

## Technical Details

**Hash algorithm**: SHA256 (64 hex characters)

**Database tables**:
- `dependency_cache`: Stores dependency layer hashes
- `combined_cache`: Stores combined environment hashes

**Lookup performance**: O(1) via indexed database queries

**Cache lifetime**: Indefinite (manual cleanup required)

---

**For more details, see**:
- Story 6-2: Dependency Layer Caching
- Story 6-3: Automatic Cache Invalidation
