# Tier 5 Plan: Advanced Features & Optimization

**Date**: 2025-11-16
**Status**: PLANNING
**Focus**: Batch management, caching, and complete file management

## Tier Overview

Tier 5 transforms RGrid from a basic distributed executor into a production-grade data processing platform with advanced batch management, content-hash caching for instant re-runs, and complete artifact management.

**Key Objectives**:
1. Complete batch execution features with progress tracking and failure handling
2. Implement content-hash caching for instant re-runs of identical scripts
3. Complete artifact management with MinIO (inputs and outputs)
4. Auto-detect Python dependencies from requirements.txt
5. Enable large file streaming and compression (>100MB files)

**Expected Outcome**: RGrid can process 1000+ files in parallel, cache script builds for instant re-runs, auto-install dependencies, and handle large files without memory issues.

---

## Prerequisites

Before starting Tier 5:

### Completed Foundation
- ✅ **Tier 4 complete** - Distributed execution working on Hetzner Cloud
- ✅ **Ray cluster operational** - Head node + auto-scaling workers
- ✅ **Hetzner auto-scaling functional** - Queue-based provisioning
- ✅ **File upload/download working** - Story 2-5 from Tier 4
- ✅ **MinIO storage configured** - S3-compatible object storage

### Required Capabilities
- ✅ Jobs distributed across multiple workers
- ✅ File handling (upload inputs, download outputs)
- ✅ MinIO presigned URLs working
- ✅ Worker health monitoring
- ✅ Auto-scaling based on queue depth

### Environment Setup
- [ ] **Tier 4.5 complete** - Basic batch execution (`--batch` flag)
- [ ] Database storage increased for artifact metadata
- [ ] MinIO lifecycle policies configured (30-day retention)
- [ ] Cache observability instrumented (hit rate monitoring)

---

## Stories Included

### Phase 1: MinIO Storage Foundation

#### Story 7-2: Auto-Collect Output Files from Container
**Epic**: Epic 7 - Artifact Management
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (MinIO SDK straightforward)

**Why**: Storage infrastructure needed for all artifact management. Currently outputs go to stdout/stderr only.

**Acceptance Criteria**:
- [ ] Runner scans `/work` directory after script execution completes
- [ ] All files in `/work` uploaded to MinIO: `executions/<exec_id>/outputs/`
- [ ] Each artifact recorded in database: filename, size, content_type, s3_key
- [ ] Runner reports upload success/failure in logs
- [ ] Empty `/work` directory doesn't cause errors
- [ ] Binary files (images, PDFs) uploaded correctly
- [ ] Subdirectories in `/work` preserved in S3 path

**Success Metric**: Script creates 5 output files, all appear in MinIO and database

**Story File**: `docs/sprint-artifacts/stories/7-2-auto-collect-outputs.md`

---

#### Story 7-3: Store Outputs in MinIO with Retention Policy
**Epic**: Epic 7 - Artifact Management
**Priority**: Critical
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (MinIO lifecycle feature)

**Why**: Prevent infinite storage growth. 30-day retention balances usability and cost.

**Acceptance Criteria**:
- [ ] MinIO bucket `rgrid-executions` configured with lifecycle policy
- [ ] Policy: objects auto-expire after 30 days
- [ ] `artifacts` table includes `expires_at` column (created_at + 30 days)
- [ ] CLI warns user when downloading near-expiry artifacts: "Expires in 2 days"
- [ ] Expired artifacts return 404 when accessed
- [ ] Lifecycle policy testable via MinIO admin console
- [ ] Documentation explains retention policy to users

**Success Metric**: Upload file, verify it expires after 30 days (simulate via MinIO)

**Story File**: `docs/sprint-artifacts/stories/7-3-minIO-retention.md`

---

### Phase 2: Complete File Management

#### Story 7-1: Auto-Upload Input Files Referenced in Arguments
**Epic**: Epic 7 - Artifact Management
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (builds on Story 2-5)

**Why**: Enhance Tier 4 basic file handling with full MinIO integration and metadata tracking.

**Acceptance Criteria**:
- [ ] CLI detects files via `os.path.isfile()` in arguments
- [ ] Files uploaded to MinIO: `executions/<exec_id>/inputs/<filename>`
- [ ] Presigned PUT URLs generated for uploads (3600s expiry)
- [ ] Upload progress shown for files >10MB: "Uploading data.csv... 45%"
- [ ] Multiple input files uploaded in parallel
- [ ] Input files recorded in `artifacts` table with metadata
- [ ] Handles relative paths, absolute paths, and symlinks
- [ ] Error handling for missing files, permission errors

**Success Metric**: `rgrid run script.py input1.csv input2.json` uploads both files correctly

**Story File**: `docs/sprint-artifacts/stories/7-1-auto-upload-inputs.md`

---

#### Story 7-4: Auto-Download Outputs to Current Directory
**Epic**: Epic 7 - Artifact Management
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (MinIO SDK)

**Why**: Complete the file workflow - users expect outputs to appear locally after execution.

**Acceptance Criteria**:
- [ ] CLI downloads all outputs from MinIO after execution completes
- [ ] Downloads to current working directory by default
- [ ] Presigned GET URLs generated for downloads (3600s expiry)
- [ ] Parallel downloads for multiple files
- [ ] Progress shown for files >10MB: "Downloading result.png... 67%"
- [ ] Subdirectory structure preserved during download
- [ ] Handles filename conflicts: `output.csv` → `output (1).csv`
- [ ] Error handling for network failures, corrupted files

**Success Metric**: Script creates 3 output files, all download automatically to local directory

**Story File**: `docs/sprint-artifacts/stories/7-4-auto-download-outputs.md`

---

#### Story 7-5: Implement --remote-only Flag to Skip Auto-Download
**Epic**: Epic 7 - Artifact Management
**Priority**: High
**Estimate**: 2-4 hours
**Complexity**: Low
**Risk**: Low (simple flag)

**Why**: Large batches don't need automatic downloads. Let users download selectively later.

**Acceptance Criteria**:
- [ ] CLI flag: `--remote-only` skips automatic download
- [ ] Displays message: "Outputs stored remotely. Download with: rgrid download exec_abc123"
- [ ] Outputs still recorded in database and MinIO
- [ ] `rgrid download <exec_id>` command downloads outputs later
- [ ] Works with both single executions and batches
- [ ] Documentation explains when to use `--remote-only`

**Success Metric**: `rgrid run script.py --remote-only` completes without downloading

**Story File**: `docs/sprint-artifacts/stories/7-5-remote-only-flag.md`

---

### Phase 3: Batch Management

#### Story 5-3: Track Batch Execution Progress
**Epic**: Epic 5 - Batch Execution
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (polling logic)

**Why**: Users need visibility into long-running batch operations (100+ files).

**Acceptance Criteria**:
- [ ] Poll API for execution statuses every 2 seconds
- [ ] Display counts: completed, failed, running, queued
- [ ] Calculate ETA based on average completion time
- [ ] Update counts in-place (single line, no scrolling)
- [ ] Show percentage: "Progress: 47/100 (47%) | ETA: 3m 20s"
- [ ] Handle edge cases: all queued, all failed, mixed states
- [ ] Ctrl+C exits gracefully (executions continue in background)
- [ ] Works for batches of 1 to 1000+ executions

**Success Metric**: Submit 100-job batch, see real-time progress updates

**Story File**: `docs/sprint-artifacts/stories/5-3-batch-progress.md`

---

#### Story 5-4: Organize Batch Outputs by Input Filename
**Epic**: Epic 5 - Batch Execution
**Priority**: High
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (filesystem operations)

**Why**: Processing 100 files creates 100 outputs - need organized structure.

**Acceptance Criteria**:
- [ ] Default: `./outputs/<input-name>/` directories created
- [ ] Input filename extracted from execution metadata
- [ ] Flag: `--output-dir custom/path` changes base directory
- [ ] Flag: `--flat` puts all outputs in single directory (no subdirs)
- [ ] Handles duplicate input names: `data.csv` from different paths
- [ ] Preserves output subdirectories: `/work/results/output.csv` → `./outputs/input1/results/output.csv`
- [ ] Documentation explains directory structure with examples

**Success Metric**: Process 10 files, outputs organized as `./outputs/file1/`, `./outputs/file2/`, etc.

**Story File**: `docs/sprint-artifacts/stories/5-4-batch-output-organization.md`

---

#### Story 5-5: Handle Batch Failures Gracefully
**Epic**: Epic 5 - Batch Execution
**Priority**: Critical
**Estimate**: 4-6 hours
**Complexity**: Medium
**Risk**: Low (error collection)

**Why**: Some files may fail - don't stop the entire batch. Show summary at end.

**Acceptance Criteria**:
- [ ] Continue processing remaining files if some fail
- [ ] Collect failed execution IDs in list
- [ ] Display final summary: "95 succeeded, 5 failed"
- [ ] List failed inputs with error messages
- [ ] Exit code = 0 if any succeeded, 1 if all failed
- [ ] Failed outputs not downloaded (only successful ones)
- [ ] Option: `--fail-fast` stops batch on first failure
- [ ] Save failure report: `batch_failures.txt` with exec IDs

**Success Metric**: Batch of 100 files where 5 fail - remaining 95 complete successfully

**Story File**: `docs/sprint-artifacts/stories/5-5-batch-failure-handling.md`

---

### Phase 4: Dependency Auto-Detection

#### Story 2-4: Auto-Detect and Install Python Dependencies
**Epic**: Epic 2 - Single Script Execution
**Priority**: High
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Medium (pip installation failures)

**Why**: Users shouldn't manually install dependencies. Auto-detect from requirements.txt.

**Acceptance Criteria**:
- [ ] Detect `requirements.txt` in script directory (same dir as script)
- [ ] Upload requirements.txt to MinIO alongside script
- [ ] Runner downloads requirements.txt into container
- [ ] Install via `pip install -r requirements.txt` before script execution
- [ ] Cache installed packages for subsequent runs (Docker layer)
- [ ] Handle missing requirements.txt gracefully (skip install step)
- [ ] Error handling for invalid requirements.txt format
- [ ] Error handling for pip installation failures
- [ ] Display install log in execution logs

**Success Metric**: Script with `numpy` in requirements.txt imports numpy successfully

**Story File**: `docs/sprint-artifacts/stories/2-4-auto-detect-dependencies.md`

---

### Phase 5: Caching System

#### Story 6-1: Implement Script Content Hashing and Cache Lookup
**Epic**: Epic 6 - Caching & Optimization
**Priority**: Critical
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (hash calculation straightforward)

**Why**: Rebuilding Docker images for identical scripts wastes time. Cache builds.

**Acceptance Criteria**:
- [ ] Calculate `script_hash = sha256(script_content + runtime)`
- [ ] Check `script_cache` table for existing hash
- [ ] If cache hit: reuse existing Docker image
- [ ] If cache miss: build new image, store hash in cache
- [ ] Cache table: script_hash, docker_image_tag, created_at
- [ ] Cache persists across executions (database-backed)
- [ ] Modified script invalidates cache (different hash)
- [ ] CLI displays cache status: "✓ Using cached build (0.2s)"
- [ ] Cache hit rate logged for observability

**Success Metric**: Run identical script twice - second run is instant (cache hit)

**Story File**: `docs/sprint-artifacts/stories/6-1-script-hash-caching.md`

---

#### Story 6-2: Implement Dependency Layer Caching
**Epic**: Epic 6 - Caching & Optimization
**Priority**: Critical
**Estimate**: 10-14 hours
**Complexity**: High (Docker layer caching complexity)
**Risk**: Medium (Docker layer management)

**Why**: Installing dependencies (numpy, pandas) is slow. Cache pip layers.

**Acceptance Criteria**:
- [ ] Calculate `deps_hash = sha256(requirements.txt content)`
- [ ] Check `dependency_cache` table for existing hash
- [ ] Use Docker BuildKit for layer caching
- [ ] Cached pip layer reused if requirements.txt unchanged
- [ ] New requirements.txt triggers fresh install + new cache
- [ ] Docker image tagged with deps_hash for layer reuse
- [ ] Cache table: deps_hash, docker_layer_id, created_at
- [ ] Handle BuildKit edge cases (cache pruning, layer conflicts)
- [ ] CLI displays: "✓ Using cached dependencies (5s vs 60s)"
- [ ] Documentation explains layer caching behavior

**Success Metric**: Script with numpy - first run installs numpy (60s), second run instant (cache)

**Story File**: `docs/sprint-artifacts/stories/6-2-dependency-layer-caching.md`

---

#### Story 6-3: Implement Automatic Cache Invalidation
**Epic**: Epic 6 - Caching & Optimization
**Priority**: Critical
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (implicit invalidation via hash change)

**Why**: Stale cache causes wrong results. Auto-invalidate when script/deps change.

**Acceptance Criteria**:
- [ ] New hash calculated on every execution
- [ ] Cache lookup fails automatically if hash doesn't match
- [ ] New Docker image built with new hash
- [ ] Old cache entries remain for historical re-runs
- [ ] No manual cache clearing needed
- [ ] Invalidation tested for:
  - Script content changes (even 1 char)
  - Requirements.txt changes
  - Runtime changes (python → node)
- [ ] Cache hit/miss logged for observability
- [ ] Documentation explains invalidation behavior

**Success Metric**: Change 1 line in script - cache miss, new build, new hash

**Story File**: `docs/sprint-artifacts/stories/6-3-cache-invalidation.md`

---

### Phase 6: Batch Retry

#### Story 5-6: Implement Retry for Failed Batch Executions
**Epic**: Epic 5 - Batch Execution
**Priority**: High
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (database query + re-submit)

**Why**: Transient failures happen. Let users retry just the failed ones.

**Acceptance Criteria**:
- [ ] API endpoint: `POST /api/v1/executions/retry`
- [ ] Accepts `batch_id` parameter to retry all failed in batch
- [ ] Filters by `batch_id + status=failed`
- [ ] Retried executions get new execution IDs
- [ ] Original failure preserved in history
- [ ] CLI command: `rgrid retry --batch batch_abc123`
- [ ] Display: "Retrying 5 failed executions from batch_abc123"
- [ ] Works with `--remote-only` flag
- [ ] Batch progress tracking works for retries

**Success Metric**: Batch with 10 failures - retry command resubmits only those 10

**Story File**: `docs/sprint-artifacts/stories/5-6-batch-retry.md`

---

### Phase 7: Optimizations

#### Story 7-6: Implement Large File Streaming and Compression
**Epic**: Epic 7 - Artifact Management
**Priority**: High
**Estimate**: 8-12 hours
**Complexity**: High
**Risk**: Medium (streaming + compression coordination)

**Why**: Loading 500MB files into memory causes OOM errors. Stream instead.

**Acceptance Criteria**:
- [ ] Stream files >100MB (not loaded into memory)
- [ ] Gzip compression for text files (CSV, JSON, TXT)
- [ ] No compression for binary files (PNG, PDF, ZIP)
- [ ] MinIO multipart uploads for files >100MB
- [ ] Auto-decompress on download (transparent to user)
- [ ] Progress bar shows MB/s throughput
- [ ] Memory usage stays <512MB even for 1GB files
- [ ] Error handling for incomplete uploads/downloads
- [ ] Documentation explains compression behavior

**Success Metric**: Upload/download 500MB CSV file - memory stays <512MB

**Story File**: `docs/sprint-artifacts/stories/7-6-large-file-streaming.md`

---

#### Story 6-4: Implement Optional Input File Caching
**Epic**: Epic 6 - Caching & Optimization
**Priority**: Medium (Nice-to-have)
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Low (similar to 6-1)

**Why**: Processing same input file 100 times shouldn't upload it 100 times.

**Acceptance Criteria**:
- [ ] Calculate `inputs_hash = sha256(all input file contents)`
- [ ] Check `input_cache` table for existing hash
- [ ] Skip upload if cache hit (files already in MinIO)
- [ ] Reuse existing S3 keys for cached inputs
- [ ] Cache table: inputs_hash, s3_keys (JSON array), created_at
- [ ] Cache invalidation: input file modified → new hash → re-upload
- [ ] CLI displays: "✓ Using cached inputs (3 files, 120MB)"
- [ ] Works with batch execution (same inputs across jobs)
- [ ] Optional: `--no-cache-inputs` flag to force re-upload

**Success Metric**: Process same 3 input files twice - second time skips upload

**Story File**: `docs/sprint-artifacts/stories/6-4-input-file-caching.md`

---

## Test Plan (REQUIRED)

### Test Strategy

**Testing Approach**: TDD (Test-Driven Development) for critical caching stories, test-after for batch/file stories

**Coverage Goals**:
- Unit tests: 80% of new code (caching logic, hash calculation)
- Integration tests: All batch workflows end-to-end
- Load testing: 1000+ file batches, 1GB files
- Cache invalidation matrix: 2-3 days dedicated testing

### Baseline Metrics (BEFORE Tier 5)

Collect these metrics BEFORE starting Tier 5:

- [ ] Batch processing throughput (jobs/minute)
- [ ] Memory usage for large file uploads
- [ ] Docker build time for script with dependencies
- [ ] Cache hit rate (should be 0% before caching)

### Test Cases by Phase

#### Phase 1: MinIO Storage (Stories 7-2, 7-3)

**Unit Tests** (`tests/unit/test_artifact_management.py`):
1. `test_scan_work_directory()` - Find all files in /work
2. `test_upload_to_minio()` - Upload files to S3
3. `test_record_artifact_metadata()` - Store in database
4. `test_lifecycle_policy_applied()` - MinIO retention works

**Integration Tests** (`tests/integration/test_outputs.py`):
1. `test_end_to_end_output_collection()` - Script creates files, all uploaded
2. `test_output_expiry()` - Verify 30-day expiration (simulated)

**Expected Test Count**: 4 unit tests, 2 integration tests

---

#### Phase 2: File Management (Stories 7-1, 7-4, 7-5)

**Unit Tests** (`tests/unit/test_file_management.py`):
1. `test_detect_input_files()` - Detect files in arguments
2. `test_generate_presigned_put_url()` - MinIO upload URL
3. `test_parallel_downloads()` - Multiple files simultaneously
4. `test_remote_only_flag()` - Skip downloads

**Integration Tests** (`tests/integration/test_files_e2e.py`):
1. `test_upload_download_workflow()` - Full file cycle
2. `test_large_file_upload()` - 100MB file uploads
3. `test_batch_file_organization()` - Output directories correct

**Expected Test Count**: 4 unit tests, 3 integration tests

---

#### Phase 3: Batch Management (Stories 5-3, 5-4, 5-5)

**Unit Tests** (`tests/unit/test_batch_management.py`):
1. `test_batch_progress_calculation()` - Count states correctly
2. `test_eta_calculation()` - Estimate based on average time
3. `test_output_directory_structure()` - Organize by input name
4. `test_failure_collection()` - Collect failed exec IDs

**Integration Tests** (`tests/integration/test_batch_e2e.py`):
1. `test_100_file_batch_progress()` - Track progress for large batch
2. `test_batch_with_failures()` - Some fail, others succeed
3. `test_output_organization()` - Verify directory structure

**Expected Test Count**: 4 unit tests, 3 integration tests

---

#### Phase 4: Dependencies (Story 2-4)

**Unit Tests** (`tests/unit/test_dependencies.py`):
1. `test_detect_requirements_txt()` - Find requirements file
2. `test_parse_requirements()` - Valid/invalid formats
3. `test_pip_install_success()` - Dependencies installed
4. `test_pip_install_failure()` - Handle errors

**Integration Tests** (`tests/integration/test_dependencies.py`):
1. `test_numpy_import()` - Script with numpy in requirements.txt works
2. `test_missing_requirements()` - Script works without requirements.txt

**Expected Test Count**: 4 unit tests, 2 integration tests

---

#### Phase 5: Caching (Stories 6-1, 6-2, 6-3)

**Unit Tests** (`tests/unit/test_caching.py`):
1. `test_script_hash_calculation()` - SHA256 hash consistent
2. `test_cache_lookup()` - Find existing cache entry
3. `test_deps_hash_calculation()` - requirements.txt hash
4. `test_cache_invalidation()` - Modified script misses cache

**Integration Tests** (`tests/integration/test_caching.py`):
1. `test_script_cache_hit()` - Identical script instant
2. `test_dependency_cache_hit()` - Same deps reused
3. `test_cache_miss_on_modification()` - Changed script rebuilds

**Cache Invalidation Matrix** (`tests/integration/test_cache_invalidation.py`):
1. `test_script_content_change()` - 1 char change invalidates
2. `test_requirements_change()` - Add numpy invalidates
3. `test_runtime_change()` - python → node invalidates
4. `test_cache_observability()` - Hit rate logged

**Expected Test Count**: 4 unit tests, 3 integration tests, 4 cache tests

---

#### Phase 6: Batch Retry (Story 5-6)

**Unit Tests** (`tests/unit/test_batch_retry.py`):
1. `test_filter_failed_executions()` - Query by batch_id + status
2. `test_retry_creates_new_ids()` - New execution IDs generated
3. `test_preserve_original_failure()` - History intact

**Integration Tests** (`tests/integration/test_retry.py`):
1. `test_retry_failed_batch()` - Retry 10 failed, 90 skipped
2. `test_retry_progress_tracking()` - Progress works for retries

**Expected Test Count**: 3 unit tests, 2 integration tests

---

#### Phase 7: Optimizations (Stories 7-6, 6-4)

**Unit Tests** (`tests/unit/test_optimizations.py`):
1. `test_gzip_compression()` - Text files compressed
2. `test_no_compression_binary()` - Images not compressed
3. `test_multipart_upload()` - Large files use multipart
4. `test_input_cache_lookup()` - Find cached inputs

**Integration Tests** (`tests/integration/test_large_files.py`):
1. `test_500mb_upload()` - Memory stays <512MB
2. `test_1gb_download()` - Streaming works
3. `test_input_file_caching()` - Reuse inputs across batch

**Load Tests** (`tests/load/test_tier5_performance.py`):
1. `test_1000_file_batch()` - Throughput measurement
2. `test_memory_profiling()` - 1GB file memory usage

**Expected Test Count**: 4 unit tests, 3 integration tests, 2 load tests

---

### Manual Testing Checklist

For features requiring manual validation:

- [ ] Process 1000 CSV files in batch, verify all outputs
- [ ] Test cache hit rate with repeated executions
- [ ] Upload/download 1GB file, monitor memory usage
- [ ] Verify MinIO lifecycle policy via admin console
- [ ] Test various requirements.txt (numpy, pandas, invalid)
- [ ] Batch with failures - verify graceful handling
- [ ] Retry failed batch executions
- [ ] Organize outputs by input name - verify structure

### Test Execution Timeline

- [ ] **Before Tier 5**: Collect baseline metrics
- [ ] **During implementation**: TDD for caching stories (write tests first)
- [ ] **After each story**: Run story-specific tests
- [ ] **Mid-tier (after Phase 5)**: Cache invalidation matrix (2-3 days)
- [ ] **After Tier 5 complete**: Load testing (1000+ file batches)
- [ ] **Before commit**: Full test suite passes
- [ ] **After tier completion**: Create TIER5_TEST_REPORT.md

---

## Estimates

| Story | Priority | Estimate | Type | Risk |
|-------|----------|----------|------|------|
| 7-2 | Critical | 6-8h | Storage | Low |
| 7-3 | Critical | 4-6h | Storage | Low |
| 7-1 | Critical | 6-8h | Files | Low |
| 7-4 | Critical | 6-8h | Files | Low |
| 7-5 | High | 2-4h | Files | Low |
| 5-3 | Critical | 6-8h | Batch | Low |
| 5-4 | High | 4-6h | Batch | Low |
| 5-5 | Critical | 4-6h | Batch | Low |
| 2-4 | High | 6-8h | Dependencies | Medium |
| 6-1 | Critical | 6-8h | Caching | Low |
| 6-2 | Critical | 10-14h | Caching | Medium |
| 6-3 | Critical | 4-6h | Caching | Low |
| 5-6 | High | 6-8h | Batch | Low |
| 7-6 | High | 8-12h | Optimization | Medium |
| 6-4 | Medium | 6-8h | Caching | Low |

**Total (Critical)**: ~56-80 hours (3-4 weeks)
**Total (Critical + High)**: ~86-122 hours (4-5 weeks)
**Total (All Stories)**: ~86-122 hours (4-5 weeks)

**Note**: Estimates include 20% complexity buffer based on Tier 4 learnings

---

## Implementation Strategy

### Phase 1: MinIO Storage Foundation (Week 1)
1. Story 7-2 (Auto-collect outputs)
2. Story 7-3 (Retention policy)

**Goal**: Complete artifact storage infrastructure

### Phase 2: File Management (Week 1-2)
3. Story 7-1 (Auto-upload inputs)
4. Story 7-4 (Auto-download outputs)
5. Story 7-5 (--remote-only flag)

**Goal**: Full file workflow working

### Phase 3: Batch Management (Week 2)
6. Story 5-3 (Progress tracking)
7. Story 5-4 (Output organization)
8. Story 5-5 (Failure handling)

**Goal**: Production-grade batch execution

### Phase 4: Dependencies (Week 2-3)
9. Story 2-4 (Auto-detect dependencies)

**Goal**: requirements.txt auto-install

### Phase 5: Caching (Week 3-4)
10. Story 6-1 (Script hash caching)
11. Story 6-2 (Dependency layer caching)
12. Story 6-3 (Cache invalidation)

**Goal**: Instant re-runs for identical scripts

### Cache Invalidation Testing (Mid-Tier, 2-3 days)
- Dedicated testing period after Phase 5
- All invalidation scenarios tested
- Cache observability instrumented
- Hit rate monitoring verified

### Phase 6: Batch Retry (Week 4)
13. Story 5-6 (Retry failed batches)

**Goal**: Retry failed executions easily

### Phase 7: Optimizations (Week 4-5)
14. Story 7-6 (Large file streaming)
15. Story 6-4 (Input file caching)

**Goal**: Performance optimization complete

---

## Dependencies

**Prerequisites**:
- [x] Tier 4 completed (distributed execution working)
- [ ] Tier 4.5 completed (basic batch with --batch flag)
- [x] Ray cluster operational
- [x] Hetzner auto-scaling functional
- [x] File upload/download working (Story 2-5)
- [ ] MinIO lifecycle policies configured
- [ ] Database storage increased for artifacts

**Blocks**:
- This tier blocks Tier 6 (Observability & Web Console)
- Specifically blocks WebSocket log streaming (needs batch progress)
- Blocks cost estimation (needs execution metadata)

**Story Dependencies**:
- 7-3 depends on 7-2 (outputs must exist before retention)
- 7-1 depends on 7-2 (storage foundation first)
- 7-4 depends on 7-2 (downloads need uploads)
- 7-5 depends on 7-4 (flag modifies download behavior)
- 5-3 depends on Tier 4.5 (batch execution basics)
- 5-4 depends on 5-3 (organization needs progress tracking)
- 5-5 depends on 5-4 (failure handling builds on organization)
- 6-2 depends on 6-1 (dependency caching builds on script caching)
- 6-3 depends on 6-2 (invalidation needs cache to exist)
- 5-6 depends on 6-3 (retry uses cache)
- 7-6 depends on 7-1, 7-4 (streaming builds on file management)
- 6-4 depends on 6-3, 7-6 (input caching after others complete)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache invalidation bugs | High | Critical | Comprehensive test matrix (2-3 days), cache observability instrumented, test all edge cases |
| Large file memory issues | Medium | High | Streaming implementation, memory profiling, test with 1GB+ files |
| Dependency installation failures | Medium | Medium | Graceful error handling, fallback to base image, show pip errors to user |
| Docker layer caching complexity | Medium | Medium | BuildKit deep-dive, extensive testing of layer reuse, clear invalidation logic |
| Batch coordination complexity | Low | Medium | Use battle-tested asyncio patterns, comprehensive integration tests |
| MinIO performance at scale | Low | Medium | Load testing with 1000+ files, benchmark upload/download throughput |
| File upload/download failures | Medium | Medium | Retry logic, progress resumption, error handling |

**Critical Risk: Cache Invalidation**
- **Impact**: Stale cache causes wrong results (data corruption)
- **Mitigation**: 2-3 day dedicated testing period, all scenarios covered
- **Test Matrix**: Script changes, dependency changes, input changes, runtime changes
- **Observability**: Instrument cache hit rate monitoring, alert on anomalies

---

## Definition of Done

**Story-level**:
- [ ] Story file created in `docs/sprint-artifacts/stories/`
- [ ] All acceptance criteria met (verified by tests)
- [ ] Unit tests written and passing (80%+ coverage for story code)
- [ ] Integration tests written and passing (critical workflows)
- [ ] Manual testing performed (if applicable)
- [ ] Code reviewed (self-review minimum)
- [ ] No regressions (existing 138 tests still pass)
- [ ] Committed and pushed to main
- [ ] Pre-commit hook passed (tests run automatically)

**Tier-level**:
- [ ] All critical stories completed and tested (Stories 7-2, 7-3, 7-1, 7-4, 5-3, 5-5, 6-1, 6-2, 6-3)
- [ ] All high-priority stories completed and tested (Stories 7-5, 5-4, 2-4, 5-6, 7-6)
- [ ] Cache invalidation matrix completed (2-3 days dedicated)
- [ ] Load testing with 1000+ file batches
- [ ] Memory profiling with 1GB+ files
- [ ] TIER5_SUMMARY.md created documenting what was done
- [ ] TIER5_TEST_REPORT.md created with test results and coverage metrics
- [ ] TIER5_RETROSPECTIVE.md completed (lessons learned)
- [ ] System meets tier objectives (batch, caching, large files)
- [ ] CLI help text updated with new flags
- [ ] Documentation: "Batch Execution Tutorial" added to docs/
- [ ] Documentation: "Caching Behavior" explained in docs/
- [ ] Ready for Tier 6 (Observability & Web Console)

---

## Success Criteria

**This tier is successful when**:
1. Process 1000 CSV files in parallel across distributed workers (measured: throughput >100 jobs/min)
2. Identical scripts execute instantly via cache (measured: <1s for cache hit vs 60s for cache miss)
3. Batch progress visible in real-time (measured: updates every 2s, accurate counts)
4. Failed batch executions retry individually (measured: 10 failures in 100-job batch → retry only 10)
5. Large files upload/download without memory issues (measured: 500MB file, memory <512MB)
6. Dependencies auto-detected and installed from requirements.txt (measured: numpy import works)

**Production Readiness**: 80% ready for production after this tier
- Batch execution production-ready
- Caching working (instant re-runs)
- Large file handling robust
- Still needs: Observability, web console, cost transparency (Tier 6)

---

## Notes

**Security Considerations**:
- requirements.txt injection risk: validate package names
- Large file DoS: enforce size limits (configurable max)
- Cache poisoning: hash verification on cache lookup
- MinIO access controls: presigned URLs scoped to account

**Cost Considerations**:
- MinIO storage costs (30-day retention)
- Bandwidth costs for large file transfers
- Cache storage (database + Docker images)
- Trade-off: storage cost vs rebuild time savings

**Architectural Decisions**:
- Content-hash caching (immutable, invalidation automatic)
- MinIO for artifacts (S3-compatible, self-hosted)
- Database for metadata (PostgreSQL JSONB for flexibility)
- Docker BuildKit for layer caching (standard, proven)
- Streaming for large files (memory-efficient)

**Related Documents**:
- docs/TIER_ROADMAP.md - Complete roadmap
- docs/TIER4_COMPLETION_SUMMARY.md - Previous tier results
- docs/ARCHITECTURE.md - Technical architecture
- docs/epics.md - Full story details

---

## Checklist Before Starting

- [ ] This plan reviewed and approved
- [ ] Tier 4.5 completed (basic batch execution)
- [ ] MinIO lifecycle policies configured (30-day retention)
- [ ] Database storage increased for artifact metadata
- [ ] All story files created in sprint-artifacts/stories/ (15 files)
- [ ] Test plan clearly understood (unit + integration + cache matrix)
- [ ] Dependencies verified (Tier 4 complete, Ray operational)
- [ ] Risks identified and mitigation strategies clear
- [ ] Definition of done understood by dev team
- [ ] Estimated time is realistic (4-5 weeks for 15 stories)
- [ ] Cache observability instrumentation ready
- [ ] Load testing environment prepared (1000+ files)
- [ ] Memory profiling tools ready (for 1GB+ files)

---

**Plan Status**: Ready for Review
**Next Step**: Review and approve plan, then begin Tier 5 implementation
**Expected Duration**: 4-5 weeks (86-122 hours)
**Target Completion**: [Date TBD based on start date]

---

**Created by**: Claude Code
**Date**: 2025-11-16
**Template Version**: Based on TIER4_PLAN.md
**Review Status**: Ready for team review and approval
