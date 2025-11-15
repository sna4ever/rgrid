# Epic Technical Specification: Caching & Optimization

Date: 2025-11-15
Author: BMad
Epic ID: 6
Status: Draft

---

## Overview

Epic 6 implements three-level content-hash caching to transform RGrid from "30-second first run" to "instant subsequent runs" for identical scripts, dependencies, and inputs. By computing SHA256 hashes of script content, requirements.txt, and input files, this epic enables cache hits that skip expensive Docker image builds and file uploads, dramatically improving developer experience and reducing infrastructure costs.

The caching strategy is completely invisible to users - no configuration, no manual cache management. Scripts automatically benefit from caching when re-executed, with automatic invalidation when content changes. This epic delivers on the "it just works, faster" promise while maintaining correctness through cryptographic hashing.

## Objectives and Scope

**In Scope:**
- Script content hashing (SHA256 of script source code)
- Script cache lookup and storage (map hash → Docker image ID)
- Dependency layer caching (SHA256 of requirements.txt content)
- Dependency cache lookup and reuse (map hash → pip layer ID)
- Automatic cache invalidation on content changes (new hash = cache miss)
- Input file caching (optional, SHA256 of all input files combined)
- Cache storage in database (script_cache, dependency_cache, input_cache tables)
- Cache TTL: 30 days (auto-cleanup of stale entries)

**Out of Scope:**
- Custom Docker image caching (only pre-configured runtimes in Epic 6)
- Output caching (not needed - outputs are unique per execution)
- Distributed cache coordination (single-tenant MVP, no cross-account sharing)
- Cache warming (precompute common dependencies)
- Cache analytics (cache hit rate tracking deferred to post-MVP)

## System Architecture Alignment

**Components Involved:**
- **API (api/)**: Cache lookup before submission, cache storage after build
- **Runner (runner/)**: Docker image build with cache reuse, dependency installation caching
- **Database (Postgres)**: Cache tables (script_cache, dependency_cache, input_cache)
- **Docker (on workers)**: Docker layer caching, image tagging

**Architecture Constraints:**
- Caching uses SHA256 hashing (cryptographically secure, collision-resistant)
- Cache keys are content-addressed (hash = cache key)
- Cache entries immutable (hash never changes for same content)
- Cache TTL: 30 days (balance storage costs vs. cache hit rate)
- No cache eviction needed (TTL cleanup sufficient for MVP)

**Cross-Epic Dependencies:**
- Requires Epic 2: Script execution, Docker image building
- Leverages Epic 3+4: Cached images used across all workers
- Optimizes Epic 5: Batch executions benefit most from caching (1000 identical scripts = 1 build)

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **Hash Calculator** (`common/hash.py`) | Compute SHA256 hashes for content | Script content, files | SHA256 hash string | Common Team |
| **Script Cache Service** (`api/services/script_cache.py`) | Lookup/store script cache entries | Script hash | Docker image ID or None | API Team |
| **Dependency Cache Service** (`api/services/dependency_cache.py`) | Lookup/store dependency cache entries | Requirements.txt hash | Pip layer ID or None | API Team |
| **Input Cache Service** (`api/services/input_cache.py`) | Lookup/store input file cache entries | Combined input hash | MinIO file references | API Team |
| **Docker Builder** (`runner/builder.py`) | Build Docker images with cache layers | Script, requirements, runtime | Docker image ID | Runner Team |
| **Cache Cleanup Job** (`orchestrator/cache_cleanup.py`) | Delete cache entries >30 days old | TTL threshold | Deleted cache count | Orchestrator Team |

### Data Models and Contracts

**Script Cache (Postgres `script_cache` table):**
```python
class ScriptCache(Base):
    __tablename__ = "script_cache"

    script_hash: str           # Primary key, SHA256 hash of script content
    docker_image_id: str       # Docker image ID (e.g., sha256:abc123...)
    runtime: str               # Runtime used (e.g., "python:3.11")

    created_at: datetime       # Cache entry creation time
    last_used_at: datetime     # Updated on cache hit
    use_count: int             # Number of cache hits (for analytics)

    # TTL: 30 days from last_used_at
```

**Dependency Cache (Postgres `dependency_cache` table):**
```python
class DependencyCache(Base):
    __tablename__ = "dependency_cache"

    dependency_hash: str       # Primary key, SHA256 hash of requirements.txt
    docker_layer_id: str       # Docker layer ID with installed dependencies
    runtime: str               # Base runtime (e.g., "python:3.11")

    created_at: datetime
    last_used_at: datetime
    use_count: int
```

**Input Cache (Postgres `input_cache` table):**
```python
class InputCache(Base):
    __tablename__ = "input_cache"

    input_hash: str            # Primary key, SHA256 hash of all input files (combined)
    file_references: dict      # JSON: {filename: minio_path} (files already uploaded)

    created_at: datetime
    last_used_at: datetime
    use_count: int
```

**Execution Record Updates:**
```python
# Add to executions table:
class Execution(Base):
    # ... existing fields from Epic 2 ...

    script_cache_hit: bool     # True if script cache hit
    dependency_cache_hit: bool # True if dependency cache hit
    input_cache_hit: bool      # True if input cache hit

    # Epic 6: Track cache hits for analytics
```

**Hash Calculation:**
```python
# common/hash.py
import hashlib

def calculate_script_hash(script_content: str) -> str:
    """
    Calculate SHA256 hash of script content.

    Args:
        script_content: Python script source code

    Returns:
        64-character hex string (SHA256 hash)

    Example:
        >>> calculate_script_hash("print('hello')")
        'a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447'
    """
    return hashlib.sha256(script_content.encode('utf-8')).hexdigest()

def calculate_dependency_hash(requirements_txt: str) -> str:
    """
    Calculate SHA256 hash of requirements.txt content.

    Normalizes whitespace to ensure consistent hashing.
    """
    # Normalize: strip whitespace, sort lines (deterministic hash)
    lines = [line.strip() for line in requirements_txt.splitlines() if line.strip()]
    lines.sort()  # Ensure deterministic order
    normalized = "\n".join(lines)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def calculate_input_hash(file_contents: List[bytes]) -> str:
    """
    Calculate combined SHA256 hash of multiple input files.

    Args:
        file_contents: List of file contents (bytes)

    Returns:
        SHA256 hash of concatenated file hashes (deterministic)
    """
    hasher = hashlib.sha256()
    for content in sorted(file_contents):  # Sort for deterministic order
        file_hash = hashlib.sha256(content).digest()
        hasher.update(file_hash)
    return hasher.hexdigest()
```

### APIs and Interfaces

**Script Cache Lookup (API):**
```python
# api/services/script_cache.py
async def lookup_script_cache(script_hash: str, runtime: str) -> Optional[str]:
    """
    Check if script is cached for given runtime.

    Args:
        script_hash: SHA256 hash of script content
        runtime: Runtime string (e.g., "python:3.11")

    Returns:
        Docker image ID if cache hit, None if cache miss

    Side effects:
        - Updates last_used_at and use_count on cache hit
    """
    cache_entry = await db.query(
        """
        SELECT docker_image_id FROM script_cache
        WHERE script_hash = :hash AND runtime = :runtime
        """,
        {"hash": script_hash, "runtime": runtime}
    )

    if cache_entry:
        # Update cache hit metadata
        await db.execute(
            """
            UPDATE script_cache
            SET last_used_at = NOW(), use_count = use_count + 1
            WHERE script_hash = :hash
            """,
            {"hash": script_hash}
        )
        return cache_entry["docker_image_id"]

    return None  # Cache miss

async def store_script_cache(script_hash: str, runtime: str, image_id: str):
    """
    Store script cache entry after building image.
    """
    await db.execute(
        """
        INSERT INTO script_cache (script_hash, docker_image_id, runtime, created_at, last_used_at, use_count)
        VALUES (:hash, :image_id, :runtime, NOW(), NOW(), 0)
        ON CONFLICT (script_hash) DO UPDATE SET
            docker_image_id = EXCLUDED.docker_image_id,
            last_used_at = NOW()
        """,
        {"hash": script_hash, "image_id": image_id, "runtime": runtime}
    )
```

**Dependency Cache Lookup (Runner):**
```python
# runner/builder.py
async def build_image_with_cache(
    script_content: str,
    requirements_txt: Optional[str],
    runtime: str
) -> str:
    """
    Build Docker image, using cache layers when available.

    Flow:
    1. Calculate script_hash
    2. Check script_cache → if hit, return cached image ID (skip build entirely)
    3. If miss, calculate dependency_hash (if requirements.txt exists)
    4. Check dependency_cache → if hit, use cached layer as base
    5. Build image with Dockerfile
    6. Store script_cache entry
    7. Return new image ID
    """
    script_hash = calculate_script_hash(script_content)

    # Check script cache
    cached_image = await script_cache.lookup_script_cache(script_hash, runtime)
    if cached_image:
        logger.info(f"Script cache hit: {script_hash[:8]}")
        return cached_image  # Instant execution!

    logger.info(f"Script cache miss: {script_hash[:8]}, building image")

    # Check dependency cache (if requirements.txt exists)
    base_image = runtime  # Default: python:3.11-slim
    if requirements_txt:
        dep_hash = calculate_dependency_hash(requirements_txt)
        cached_layer = await dependency_cache.lookup_dependency_cache(dep_hash, runtime)

        if cached_layer:
            logger.info(f"Dependency cache hit: {dep_hash[:8]}")
            base_image = cached_layer  # Use cached layer with pre-installed deps
        else:
            logger.info(f"Dependency cache miss: {dep_hash[:8]}")

    # Build Docker image
    dockerfile = generate_dockerfile(base_image, script_content, requirements_txt)
    image_id = await docker_client.build_image(dockerfile, tag=f"rgrid-exec:{script_hash[:12]}")

    # Store in script cache
    await script_cache.store_script_cache(script_hash, runtime, image_id)

    # Store in dependency cache (if requirements.txt and not cached)
    if requirements_txt and not cached_layer:
        # Build intermediate layer with just dependencies
        dep_layer_id = await build_dependency_layer(runtime, requirements_txt)
        await dependency_cache.store_dependency_cache(dep_hash, runtime, dep_layer_id)

    return image_id
```

**Docker Multi-Stage Build (with Caching):**
```dockerfile
# Generated Dockerfile (dependency caching)
FROM python:3.11-slim AS dependencies

# Install dependencies (cached layer)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Final stage (script-specific)
FROM dependencies

# Copy script
COPY script.py /work/script.py
WORKDIR /work

CMD ["python", "script.py"]
```

**Input Cache Usage (CLI → API):**
```python
# cli/rgrid/commands/run.py (updated for Epic 6)
async def run_script(script: Path, input_files: List[Path], ...):
    """
    Submit execution with input cache check.
    """
    # Calculate input hash (if input files provided)
    if input_files:
        file_contents = [f.read_bytes() for f in input_files]
        input_hash = calculate_input_hash(file_contents)

        # Check input cache
        cached_inputs = await api_client.lookup_input_cache(input_hash)
        if cached_inputs:
            print(f"✓ Input cache hit: skipping upload for {len(input_files)} files")
            # Use cached file references instead of uploading
            file_references = cached_inputs["file_references"]
        else:
            # Cache miss: upload files and store in cache
            file_references = await upload_input_files(input_files)
            await api_client.store_input_cache(input_hash, file_references)
    else:
        file_references = {}

    # Submit execution (API uses cached script/dependency images)
    execution_id = await api_client.create_execution(
        script_content=script.read_text(),
        input_file_references=file_references,
        ...
    )
```

### Workflows and Sequencing

**First Execution (Cache Cold - All Misses):**
```
1. USER: rgrid run process.py input.csv

2. CLI:
   a. Read script: process.py content
   b. Calculate script_hash: sha256(content) = "abc123..."
   c. Read input: input.csv (1 MB)
   d. Calculate input_hash: sha256(input.csv) = "def456..."

3. CLI → API: Submit Execution
   a. POST /api/v1/executions
   b. Body: {script_content, script_hash, input_hash, runtime: "python:3.11"}

4. API:
   a. Check script_cache: SELECT WHERE script_hash='abc123' AND runtime='python:3.11'
      → No rows (cache miss)
   b. Check input_cache: SELECT WHERE input_hash='def456'
      → No rows (cache miss)
   c. Create execution record: script_cache_hit=false, input_cache_hit=false

5. CLI: Upload input.csv to MinIO (presigned URL, 1 MB upload ~1 second)

6. RUNNER:
   a. Download input from MinIO
   b. Build Docker image:
      - No cached script image → build from scratch
      - No cached dependency layer → run pip install (20 seconds)
      - Tag image: rgrid-exec:abc123
      - Total build time: ~30 seconds
   c. Run container with input
   d. Upload outputs

7. RUNNER → API: Store Cache Entries
   a. INSERT INTO script_cache (script_hash='abc123', docker_image_id='sha256:xyz...', runtime='python:3.11')
   b. INSERT INTO input_cache (input_hash='def456', file_references={'input.csv': 's3://...'})

Total time: ~35 seconds (upload 1s + build 30s + execution 4s)
```

**Second Execution (Cache Hot - All Hits):**
```
1. USER: rgrid run process.py input.csv (identical script and input)

2. CLI:
   a. Calculate script_hash: "abc123..." (same as before)
   b. Calculate input_hash: "def456..." (same as before)

3. CLI → API: Submit Execution
   a. POST /api/v1/executions (same request)

4. API:
   a. Check script_cache: SELECT WHERE script_hash='abc123'
      → Found! docker_image_id='sha256:xyz...'
   b. Check input_cache: SELECT WHERE input_hash='def456'
      → Found! file_references={'input.csv': 's3://...'}
   c. Create execution record: script_cache_hit=true, input_cache_hit=true
   d. Update cache hit counters:
      - UPDATE script_cache SET last_used_at=NOW(), use_count=use_count+1
      - UPDATE input_cache SET last_used_at=NOW(), use_count=use_count+1

5. CLI: Skip upload (input already in MinIO, use cached reference)

6. RUNNER:
   a. Skip download (input already cached on worker - future optimization)
   b. Skip Docker build (use cached image: sha256:xyz...)
      - Total build time: 0 seconds!
   c. Run container immediately
   d. Upload outputs

Total time: ~4 seconds (execution only, no upload/build overhead)

Performance improvement: 35s → 4s = 8.75x faster!
```

**Cache Invalidation (Script Modified):**
```
1. USER: Edits process.py (adds 1 line of code)

2. USER: rgrid run process.py input.csv

3. CLI:
   a. Calculate script_hash: "ghi789..." (NEW HASH, different from "abc123")
   b. Calculate input_hash: "def456..." (same)

4. API:
   a. Check script_cache: SELECT WHERE script_hash='ghi789'
      → No rows (cache miss, automatic invalidation!)
   b. Check input_cache: SELECT WHERE input_hash='def456'
      → Found! (input unchanged)

5. RUNNER:
   a. Input cache hit: skip upload
   b. Script cache miss: rebuild image (~30 seconds)
   c. Store new cache entry: script_hash='ghi789', new image ID

Result: Automatic cache invalidation via content hashing (no manual cache clearing needed)
```

**Cache Cleanup (Background Job):**
```
# orchestrator/cache_cleanup.py (runs daily)

async def cleanup_stale_cache_entries():
    """
    Delete cache entries older than 30 days (TTL).
    """
    # Script cache
    deleted_scripts = await db.execute(
        "DELETE FROM script_cache WHERE last_used_at < NOW() - INTERVAL '30 days' RETURNING script_hash"
    )

    # Dependency cache
    deleted_deps = await db.execute(
        "DELETE FROM dependency_cache WHERE last_used_at < NOW() - INTERVAL '30 days' RETURNING dependency_hash"
    )

    # Input cache
    deleted_inputs = await db.execute(
        "DELETE FROM input_cache WHERE last_used_at < NOW() - INTERVAL '30 days' RETURNING input_hash"
    )

    logger.info(f"Cleaned up cache: {len(deleted_scripts)} scripts, "
                f"{len(deleted_deps)} dependencies, {len(deleted_inputs)} inputs")

    # TODO: Delete unused Docker images from workers (deferred to post-MVP)
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Cache hit latency**: < 10ms for database lookup (indexed query)
- **Hash calculation time**: < 100ms for 10 MB script (SHA256 is fast)
- **Cache hit rate** (after warmup): 80%+ for typical dev workflows
  - Developer runs same script 10 times → 1 miss, 9 hits = 90% hit rate
- **Storage overhead**: ~1 KB per cache entry (hash + metadata)
  - 10,000 cached scripts = 10 MB database storage (negligible)

**Performance Gains:**
- **First run**: 30-35 seconds (build + upload + execution)
- **Cached run**: 4-5 seconds (execution only)
- **Speedup**: 6-8x faster for repeated executions
- **Batch benefits**: 1000-file batch with identical script = 1 build + 999 cache hits

**Source:** Architecture performance targets

### Security

**Cache Isolation:**
- All cache entries scoped to account (no cross-account cache sharing in MVP)
- Cache keys are cryptographically secure (SHA256 collision-resistant)
- Cache poisoning impossible (hash uniquely identifies content)

**Source:** Architecture security decisions

### Reliability/Availability

**Cache Correctness:**
- Content-hash ensures cache hits are always correct (no stale cache bugs)
- Cache invalidation is automatic (new content → new hash → cache miss)
- No manual cache management needed

**Fault Tolerance:**
- **Cache database unavailable**: Fall back to no caching (build every time, degraded performance)
- **Stale cache entries**: TTL cleanup prevents unbounded growth

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Cache hit rate (hits / (hits + misses)) by cache type (script, dependency, input)
- Cache size (total entries, storage used)
- Average cache age (time since last_used_at)
- Cache cleanup count (entries deleted per run)

**Logging:**
- API: Cache hit/miss events with hash prefix
- Runner: Image build skipped (cache hit) vs. image built (cache miss)

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Python Standard Library:**
- `hashlib` (built-in): SHA256 hashing

**Database Schema:**
```sql
-- Script cache
CREATE TABLE script_cache (
    script_hash VARCHAR(64) PRIMARY KEY,  -- SHA256 hex string
    docker_image_id VARCHAR(128) NOT NULL,
    runtime VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    use_count INT DEFAULT 0
);

CREATE INDEX idx_script_cache_last_used ON script_cache(last_used_at);

-- Dependency cache
CREATE TABLE dependency_cache (
    dependency_hash VARCHAR(64) PRIMARY KEY,
    docker_layer_id VARCHAR(128) NOT NULL,
    runtime VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    use_count INT DEFAULT 0
);

CREATE INDEX idx_dependency_cache_last_used ON dependency_cache(last_used_at);

-- Input cache
CREATE TABLE input_cache (
    input_hash VARCHAR(64) PRIMARY KEY,
    file_references JSONB NOT NULL,  -- {filename: minio_path}
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    use_count INT DEFAULT 0
);

CREATE INDEX idx_input_cache_last_used ON input_cache(last_used_at);

-- Update executions table
ALTER TABLE executions ADD COLUMN script_cache_hit BOOLEAN DEFAULT false;
ALTER TABLE executions ADD COLUMN dependency_cache_hit BOOLEAN DEFAULT false;
ALTER TABLE executions ADD COLUMN input_cache_hit BOOLEAN DEFAULT false;
```

**Docker Image Tagging:**
- Cached images tagged with script_hash: `rgrid-exec:abc123`
- Enables lookup by hash instead of rebuilding

## Acceptance Criteria (Authoritative)

**AC-6.1: Script Content Hashing and Cache Lookup**
1. When execution is submitted, API calculates SHA256 hash of script content
2. API checks script_cache table for existing hash + runtime
3. If cache hit, execution uses cached Docker image (no build)
4. If cache miss, runner builds new image and stores in cache

**AC-6.2: Dependency Layer Caching**
1. When script has requirements.txt, API calculates hash of requirements content
2. API checks dependency_cache for existing hash + runtime
3. If cache hit, Docker build uses cached layer (skip pip install)
4. If cache miss, runner installs dependencies and caches layer

**AC-6.3: Automatic Cache Invalidation**
1. When script content changes, new hash is calculated
2. New hash does not match cache → cache miss → rebuild
3. Old cache entry remains valid (for reverting changes)
4. No manual cache clearing required

**AC-6.4: Optional Input File Caching**
1. When input files provided, CLI calculates combined hash of all files
2. CLI checks input_cache for existing hash
3. If cache hit, skip upload (use cached MinIO references)
4. If cache miss, upload files and store cache entry

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-6.1 | Services: Script Cache | api/services/script_cache.py | Submit same script twice, verify cache hit on second execution |
| AC-6.2 | Services: Dependency Cache | runner/builder.py | Submit script with requirements.txt twice, verify pip install skipped on second |
| AC-6.3 | Workflows: Cache Invalidation | Hash calculation | Modify script, submit, verify new hash and cache miss |
| AC-6.4 | Services: Input Cache | cli/commands/run.py | Submit with same input twice, verify upload skipped on second |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Cache database grows unbounded without cleanup
   - **Mitigation**: TTL cleanup job (30 days), runs daily
2. **R2**: Hash collisions (extremely unlikely with SHA256)
   - **Mitigation**: SHA256 is collision-resistant (2^256 space, negligible risk)
3. **R3**: Cached Docker images consume worker disk space
   - **Mitigation**: Docker image pruning (weekly), future: coordinated cache eviction

**Assumptions:**
1. **A1**: Script content is deterministic (same hash = same behavior)
2. **A2**: Requirements.txt is normalized (whitespace differences don't break cache)
3. **A3**: 30-day TTL is sufficient (most scripts re-run within 30 days or abandoned)
4. **A4**: Cache hit rate >80% in practice (based on typical dev workflows)

**Open Questions:**
1. **Q1**: Should we cache custom Docker images (user-provided Dockerfiles)?
   - **Decision**: Deferred to post-MVP (complex invalidation logic)
2. **Q2**: Should cache be shared across accounts (public cache for common scripts)?
   - **Decision**: No, security risk (cache poisoning), single-tenant MVP
3. **Q3**: Should we implement cache warming (pre-build common images)?
   - **Decision**: Deferred, focus on automatic caching first

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Hash calculation: Test SHA256 with various inputs, verify deterministic
   - Cache lookup: Mock database, verify hit/miss logic
   - Cache invalidation: Modify content, verify new hash

2. **Integration Tests**
   - Script cache: Submit script, verify image cached, submit again, verify cache hit
   - Dependency cache: Submit with requirements.txt, verify cached layer reused
   - Input cache: Submit with inputs, verify upload skipped on second submission

3. **End-to-End Tests**
   - Complete flow: First run (cold) → measure time, second run (warm) → verify faster
   - Cache invalidation: Run → modify script → run again → verify rebuild
   - TTL cleanup: Create cache entry with old last_used_at → run cleanup → verify deleted

**Frameworks:**
- **Hash testing**: Standard Python unittest for SHA256
- **Cache logic**: pytest with mock database
- **E2E**: Real executions, measure timing differences

**Coverage of ACs:**
- AC-6.1: Integration test (submit twice, verify cache hit)
- AC-6.2: Integration test (submit with requirements.txt, verify cached layer)
- AC-6.3: E2E test (modify script, verify cache miss)
- AC-6.4: Integration test (submit with inputs, verify upload skipped)

**Edge Cases:**
- Empty script (hash of empty string)
- Script with non-ASCII characters (UTF-8 encoding)
- Requirements.txt with different whitespace (normalization)
- Input files with identical content but different names (hash same)
- Cache entry deleted mid-execution (fallback to rebuild)

**Performance Tests:**
- Measure cold run time: 30-35 seconds
- Measure warm run time: 4-5 seconds
- Verify cache hit latency: <10ms

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 6.1
