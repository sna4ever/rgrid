# Epic Technical Specification: Batch Execution & Parallelism

Date: 2025-11-15
Author: BMad
Epic ID: 5
Status: Draft

---

## Overview

Epic 5 implements RGrid's "killer feature" - the ability to scale from running a single script to processing 1000+ files in parallel with a single command. By introducing the `--batch` flag with glob pattern expansion and the `--parallel` flag for concurrency control, this epic transforms RGrid into a powerful parallel data processing platform.

The implementation enables users to execute `rgrid run process.py --batch data/*.csv` and have each CSV file processed independently across the distributed worker pool, with automatic progress tracking, organized output directories, graceful failure handling, and selective retry capabilities. This epic demonstrates the full power of the auto-scaling infrastructure (Epic 4) and distributed orchestration (Epic 3).

## Objectives and Scope

**In Scope:**
- `--batch` flag with glob pattern expansion (e.g., `data/*.csv`, `inputs/**/*.json`)
- Individual execution creation per matched file
- `--parallel` flag to control max concurrent executions (default: 10)
- Real-time progress tracking (completed/failed/running/queued counts)
- Progress bar and ETA calculation for batch operations
- Organized output directories: `./outputs/<input-name>/`
- `--output-dir` flag to override output location
- `--flat` flag for flat output structure (no subdirectories)
- Graceful batch failure handling (continue processing on individual failures)
- Batch retry command: `rgrid retry --batch <batch-id> --failed-only`

**Out of Scope:**
- Real-time log streaming (Epic 8)
- Cost estimation for batch jobs (covered in Epic 9)
- WebSocket progress updates (Epic 8)
- Advanced retry strategies (exponential backoff, Epic 10)
- Batch job templating or loops (MVP supports glob patterns only)

## System Architecture Alignment

**Components Involved:**
- **CLI (cli/)**: Batch command parsing, glob expansion, parallel submission, progress tracking
- **API (api/)**: Batch metadata tracking, batch status aggregation
- **Database (Postgres)**: Batch record, execution-batch relationships
- **Ray + Orchestrator**: Parallel task distribution across workers (leverages Epic 3+4)

**Architecture Constraints:**
- Batch operations are CLI-orchestrated (API does not batch-submit automatically)
- Each file in batch creates independent execution record
- Batch ID links related executions for status queries
- Default parallelism: 10 (configurable via --parallel flag)
- CLI uses asyncio.Semaphore for concurrency control (client-side throttling)
- Progress tracking via polling (10-second intervals until Epic 8 adds WebSocket)

**Cross-Epic Dependencies:**
- Requires Epic 1: CLI framework, API infrastructure
- Requires Epic 2: Single execution logic
- Leverages Epic 3: Ray distributes batch across workers
- Leverages Epic 4: Auto-scaling provisions workers for large batches
- Enables Epic 6: Batch operations benefit most from caching
- Feeds Epic 8: Progress tracking upgraded to WebSocket streaming

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **CLI Batch Expander** (`cli/rgrid/batch/expander.py`) | Expand glob patterns to file list | Glob pattern (e.g., data/*.csv) | List of file paths | CLI Team |
| **CLI Batch Executor** (`cli/rgrid/batch/executor.py`) | Submit executions in parallel, track progress | File list, --parallel flag | Batch ID, progress stats | CLI Team |
| **CLI Progress Tracker** (`cli/rgrid/batch/progress.py`) | Poll batch status, display progress bar, calculate ETA | Batch ID | Real-time progress display | CLI Team |
| **API Batch Service** (`api/services/batch.py`) | Create batch record, aggregate execution statuses | Batch metadata | Batch ID, status summary | API Team |
| **CLI Output Organizer** (`cli/rgrid/batch/outputs.py`) | Download and organize batch outputs by input name | Batch ID, output directory | Organized file structure | CLI Team |
| **CLI Retry Handler** (`cli/rgrid/commands/retry.py`) | Retry failed executions from batch | Batch ID, --failed-only flag | New batch with retried executions | CLI Team |

### Data Models and Contracts

**Batch Record (Postgres `batches` table):**
```python
class Batch(Base):
    __tablename__ = "batches"

    batch_id: str              # Primary key, format: batch_{uuid}
    account_id: str            # Foreign key to accounts
    script_content: str        # Script executed for all files in batch
    script_filename: str       # e.g., "process.py"
    runtime: str               # Runtime used for all executions

    glob_pattern: str          # Original pattern (e.g., "data/*.csv")
    total_files: int           # Number of files matched
    max_parallel: int          # --parallel flag value (default 10)

    created_at: datetime       # Batch submission time
    completed_at: datetime     # When last execution finished (null if running)

    # Status summary (updated as executions complete)
    status: str                # queued|running|completed|partial_failure|failed
    completed_count: int       # count(status='completed')
    failed_count: int          # count(status='failed')
    running_count: int         # count(status='running')
    queued_count: int          # count(status='queued')
```

**Execution-Batch Relationship (Update `executions` table):**
```python
# Add to executions table from Epic 2:
class Execution(Base):
    # ... existing fields ...

    batch_id: str              # Foreign key to batches (null for single executions)
    batch_input_file: str      # Original input filename (e.g., "data1.csv")
    batch_index: int           # Execution order within batch (0, 1, 2, ...)
```

**Batch Status Response:**
```python
# GET /api/v1/batches/{batch_id}/status
class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str                # queued|running|completed|partial_failure|failed
    total_files: int

    completed_count: int
    failed_count: int
    running_count: int
    queued_count: int

    progress_percent: float    # completed_count / total_files * 100
    estimated_completion_time: Optional[datetime]  # Based on avg execution time

    created_at: datetime
    completed_at: Optional[datetime]
```

**Progress Tracker State:**
```python
@dataclass
class BatchProgress:
    """CLI-side progress tracking state."""
    batch_id: str
    total_files: int
    max_parallel: int

    submitted: int             # Files submitted so far (0 to total_files)
    completed: int             # Executions completed
    failed: int                # Executions failed
    running: int               # Executions currently running

    avg_duration: float        # Average execution time (seconds)
    eta_seconds: float         # Estimated time to completion
    elapsed_seconds: float     # Time since batch started
```

### APIs and Interfaces

**CLI Batch Submission Flow:**
```python
# cli/rgrid/batch/executor.py
async def execute_batch(
    script: Path,
    glob_pattern: str,
    runtime: str = "python:3.11",
    max_parallel: int = 10,
    output_dir: Path = Path("./outputs"),
    flat: bool = False,
    watch: bool = False
) -> str:
    """
    Execute script across all files matching glob pattern.

    Args:
        script: Path to script file
        glob_pattern: Glob pattern (e.g., "data/*.csv")
        runtime: Docker runtime
        max_parallel: Max concurrent executions (default 10)
        output_dir: Output directory (default ./outputs)
        flat: Flat output structure (no subdirectories)
        watch: Real-time progress tracking

    Returns:
        Batch ID

    Flow:
    1. Expand glob pattern to file list
    2. Create batch record via API
    3. Submit executions with semaphore (max_parallel concurrency)
    4. If --watch: Show progress bar and poll status
    5. Download outputs when complete
    """
    # 1. Expand glob pattern
    files = glob.glob(glob_pattern, recursive=True)
    if not files:
        raise ValueError(f"No files matched pattern: {glob_pattern}")

    # 2. Read script content
    script_content = script.read_text()

    # 3. Create batch record
    batch = await api_client.create_batch(
        script_content=script_content,
        script_filename=script.name,
        runtime=runtime,
        glob_pattern=glob_pattern,
        total_files=len(files),
        max_parallel=max_parallel
    )
    batch_id = batch["batch_id"]

    print(f"Starting batch: {len(files)} files, {max_parallel} parallel")

    # 4. Submit executions with concurrency control
    semaphore = asyncio.Semaphore(max_parallel)
    tasks = []

    async def submit_execution(file_path: Path, index: int):
        async with semaphore:  # Limit concurrency
            exec_id = await api_client.create_execution(
                script_content=script_content,
                script_filename=script.name,
                runtime=runtime,
                args=[str(file_path)],
                batch_id=batch_id,
                batch_input_file=file_path.name,
                batch_index=index
            )
            return exec_id

    for index, file_path in enumerate(files):
        task = asyncio.create_task(submit_execution(Path(file_path), index))
        tasks.append(task)

    # Wait for all submissions (not completions!)
    execution_ids = await asyncio.gather(*tasks)

    print(f"✓ Submitted {len(execution_ids)} executions")

    # 5. If --watch: Show progress
    if watch:
        await track_batch_progress(batch_id, total_files=len(files))

    # 6. Download outputs (organized by input filename)
    if not watch:
        print(f"Batch running in background. Track progress: rgrid status --batch {batch_id}")
    else:
        await download_batch_outputs(batch_id, output_dir, flat)

    return batch_id
```

**API Batch Creation:**
```
POST /api/v1/batches
Authorization: Bearer {api_key}
Content-Type: application/json

Request:
{
  "script_content": "import sys; print(f'Processing {sys.argv[1]}')",
  "script_filename": "process.py",
  "runtime": "python:3.11",
  "glob_pattern": "data/*.csv",
  "total_files": 100,
  "max_parallel": 10
}

Response (200 OK):
{
  "batch_id": "batch_abc123",
  "status": "queued",
  "total_files": 100,
  "created_at": "2025-11-15T10:30:00Z"
}
```

**API Batch Status Aggregation:**
```
GET /api/v1/batches/{batch_id}/status
Authorization: Bearer {api_key}

Response:
{
  "batch_id": "batch_abc123",
  "status": "running",
  "total_files": 100,
  "completed_count": 45,
  "failed_count": 3,
  "running_count": 10,
  "queued_count": 42,
  "progress_percent": 45.0,
  "estimated_completion_time": "2025-11-15T10:35:00Z",
  "created_at": "2025-11-15T10:30:00Z",
  "completed_at": null
}
```

**Progress Display (CLI Output):**
```
# cli/rgrid/batch/progress.py
async def track_batch_progress(batch_id: str, total_files: int):
    """
    Poll batch status and display progress bar.
    Updates every 2 seconds until batch completes.
    """
    start_time = time.time()

    while True:
        status = await api_client.get_batch_status(batch_id)

        # Calculate progress
        completed = status["completed_count"]
        failed = status["failed_count"]
        running = status["running_count"]
        queued = status["queued_count"]

        progress = (completed + failed) / total_files
        elapsed = time.time() - start_time

        # Calculate ETA
        if completed > 0:
            avg_duration = elapsed / (completed + failed)
            remaining = queued + running
            eta_seconds = remaining * avg_duration
            eta_str = format_duration(eta_seconds)
        else:
            eta_str = "calculating..."

        # Display progress bar
        bar = render_progress_bar(progress, width=40)
        print(f"\r{bar} {completed}/{total_files} complete "
              f"({failed} failed, {running} running, {queued} queued) "
              f"| ETA: {eta_str}", end="")

        # Check completion
        if status["status"] in ["completed", "partial_failure", "failed"]:
            print()  # Newline
            break

        await asyncio.sleep(2)  # Poll every 2 seconds

    # Final summary
    if status["status"] == "completed":
        print(f"✓ Batch complete: {completed} succeeded, {failed} failed")
    elif status["status"] == "partial_failure":
        print(f"⚠ Batch partial: {completed} succeeded, {failed} failed")
    elif status["status"] == "failed":
        print(f"✗ Batch failed: {completed} succeeded, {failed} failed")
```

### Workflows and Sequencing

**Batch Execution End-to-End:**
```
1. USER: rgrid run process.py --batch data/*.csv --parallel 20 --watch

2. CLI BATCH EXPANDER:
   a. Expand glob: data/*.csv → [data1.csv, data2.csv, ..., data100.csv]
   b. Validate files exist: 100 files found
   c. Read script: process.py

3. CLI → API: Create Batch
   a. POST /api/v1/batches
   b. API creates batch record: batch_abc123, total_files=100
   c. API returns batch_id

4. CLI BATCH EXECUTOR:
   a. Create semaphore: max_parallel=20
   b. Loop through files (100 files):
      i.   Acquire semaphore slot (wait if 20 in flight)
      ii.  POST /api/v1/executions (script, runtime, args=[file])
      iii. Release semaphore when submission completes
   c. All 100 executions submitted within ~10 seconds

5. API (for each execution):
   a. Create execution record: execution_id, batch_id, batch_input_file
   b. Submit Ray task: execute_script.remote(execution_id)
   c. Return execution_id to CLI

6. RAY + WORKERS (Epic 3+4 infrastructure):
   a. Ray distributes 100 tasks across available workers
   b. Orchestrator provisions workers as needed (queue depth → auto-scale)
   c. Workers execute scripts in parallel (2 jobs per CX22 worker)
   d. Executions complete at different rates (30s - 2 minutes per file)

7. CLI PROGRESS TRACKER (--watch flag):
   a. Poll API every 2 seconds: GET /api/v1/batches/{batch_id}/status
   b. Display progress bar:
      [=========>           ] 45/100 complete (3 failed, 10 running, 42 queued)
      Duration: 2m 30s | ETA: 3m 15s
   c. Update until batch completes

8. API BATCH STATUS AGGREGATION (on each poll):
   a. Query executions table:
      SELECT status, COUNT(*) FROM executions WHERE batch_id='batch_abc123' GROUP BY status
   b. Calculate: completed=45, failed=3, running=10, queued=42
   c. Calculate progress_percent: (45+3)/100 = 48%
   d. Estimate ETA: avg_duration=60s, remaining=52, eta=52*60=52 minutes
   e. Return status summary

9. BATCH COMPLETION:
   a. All executions reach terminal state (completed or failed)
   b. API updates batch: status=completed (or partial_failure if any failed)
   c. CLI progress tracker exits

10. CLI OUTPUT ORGANIZER:
    a. Query API: GET /api/v1/batches/{batch_id}/executions
    b. For each execution:
       - Download outputs from MinIO (presigned URLs)
       - Organize: ./outputs/{batch_input_file}/output.json
    c. Result:
       ./outputs/
         data1/
           output.json
         data2/
           output.json
         ...
    d. Display: "✓ Downloaded outputs to ./outputs/"
```

**Batch Retry Flow:**
```
1. USER: rgrid retry --batch batch_abc123 --failed-only

2. CLI → API: Get Batch Status
   a. GET /api/v1/batches/{batch_id}/status
   b. Response: 95 completed, 5 failed

3. CLI → API: Get Failed Executions
   a. GET /api/v1/batches/{batch_id}/executions?status=failed
   b. Response: [exec_1, exec_2, exec_3, exec_4, exec_5]
   c. Extract batch_input_file for each: [data10.csv, data25.csv, ...]

4. CLI: Create New Batch (Retry Batch)
   a. Same script, runtime, but only failed files
   b. POST /api/v1/batches (total_files=5, glob_pattern="retry")
   c. API returns: batch_def456 (new batch ID)

5. CLI: Submit Retry Executions
   a. For each failed execution:
      - POST /api/v1/executions (same args, new batch_id=batch_def456)
   b. 5 new executions submitted

6. CLI: Display
   a. "Retrying 5 failed executions from batch_abc123"
   b. "New batch ID: batch_def456"
   c. "Track progress: rgrid status --batch batch_def456"
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Batch submission time**: < 5 seconds for 100 files (API submission overhead)
  - Each execution submission: ~50ms
  - 100 files with max_parallel=20: ~250ms (5 rounds × 50ms)
- **Glob expansion time**: < 1 second for 10,000 files
  - Python glob.glob() is fast for filesystem patterns
- **Progress polling overhead**: < 100ms per poll (batch status query)
  - Single aggregation query with GROUP BY
- **Output download time**: Depends on output size (10 MB/s download rate)
  - 100 files × 1 MB each = 100 MB → ~10 seconds

**Scalability:**
- Support batches up to 10,000 files (practical limit for MVP)
- CLI handles 100 concurrent submissions without blocking (asyncio)
- Database query performance: <100ms for batch status (indexed batch_id)

**Source:** Architecture performance targets

### Security

**Batch Authorization:**
- All batch executions must belong to same account (batch_id → account_id check)
- Users can only retry their own batches (API enforces ownership)

**Glob Pattern Safety:**
- Glob patterns executed on client filesystem (no server-side file access)
- CLI validates patterns don't escape intended directory (optional: flag for --allow-absolute-paths)

**Source:** Architecture security patterns

### Reliability/Availability

**Fault Tolerance:**
- **Individual execution failures**: Don't abort batch (continue processing remaining files)
- **CLI crash mid-batch**: Batch continues in background (can reconnect with --watch)
- **Network blip during submission**: CLI retries failed submissions (exponential backoff)

**Batch Guarantees:**
- Each file processed at most once (no duplicate submissions within batch)
- Failed files can be retried via `--failed-only` flag
- Batch status eventually consistent (polling lag: 2 seconds max)

**Error Handling:**
- If 100% of batch fails: batch status=failed
- If some succeed, some fail: batch status=partial_failure
- CLI displays clear summary: "95 succeeded, 5 failed"

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Batch count (total, by status: running, completed, failed)
- Average batch size (files per batch)
- Batch completion rate (batches/hour)
- Failed file ratio (failed / total across all batches)

**Logging:**
- CLI: Batch submission events, progress updates, output downloads
- API: Batch creation, status queries, aggregation times

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Python Dependencies (CLI):**
```toml
# cli/pyproject.toml
[tool.poetry.dependencies]
glob2 = "^0.7"          # Enhanced glob with recursive ** support (or use standard glob)
rich = "^13.7.0"        # Progress bar rendering
asyncio = "built-in"    # Concurrency control
```

**Database Schema Updates:**
```sql
-- New table: batches
CREATE TABLE batches (
    batch_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) REFERENCES accounts(account_id),
    script_content TEXT NOT NULL,
    script_filename VARCHAR(255),
    runtime VARCHAR(64),
    glob_pattern TEXT,
    total_files INT,
    max_parallel INT DEFAULT 10,

    status VARCHAR(32) DEFAULT 'queued',  -- queued|running|completed|partial_failure|failed
    completed_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    running_count INT DEFAULT 0,
    queued_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Index for batch status queries
CREATE INDEX idx_batches_account ON batches(account_id, created_at DESC);
CREATE INDEX idx_batches_status ON batches(status);

-- Update executions table
ALTER TABLE executions ADD COLUMN batch_id VARCHAR(64) REFERENCES batches(batch_id);
ALTER TABLE executions ADD COLUMN batch_input_file VARCHAR(255);
ALTER TABLE executions ADD COLUMN batch_index INT;

-- Index for batch execution queries
CREATE INDEX idx_executions_batch ON executions(batch_id, status);
```

**API Endpoints (New):**
```
POST   /api/v1/batches                    # Create batch
GET    /api/v1/batches/{batch_id}         # Get batch details
GET    /api/v1/batches/{batch_id}/status  # Get aggregated status
GET    /api/v1/batches/{batch_id}/executions?status={status}  # List executions
```

## Acceptance Criteria (Authoritative)

**AC-5.1: Batch Flag with Glob Expansion**
1. When I run `rgrid run script.py --batch data/*.csv`, CLI expands glob to all matching files
2. CLI creates one execution per file
3. Each execution receives input file as argument
4. CLI displays: "Starting batch: 100 files, 10 parallel"

**AC-5.2: Parallel Flag for Concurrency Control**
1. When I run `--batch data/*.csv --parallel 20`, CLI submits max 20 executions concurrently
2. As executions complete, CLI submits next executions (queue pattern)
3. Total concurrent executions never exceeds --parallel value

**AC-5.3: Batch Progress Tracking**
1. With `--watch` flag, CLI displays real-time progress bar
2. Progress shows: completed, failed, running, queued counts
3. ETA calculated based on average execution time
4. Progress updates every 2 seconds

**AC-5.4: Organize Outputs by Input Filename**
1. Batch outputs downloaded to `./outputs/<input-name>/`
2. Each subdirectory contains outputs for that input file
3. Directory structure: ./outputs/data1/, ./outputs/data2/, etc.

**AC-5.5: Graceful Batch Failure Handling**
1. If some executions fail, CLI continues processing remaining files
2. Final summary shows: "95 succeeded, 5 failed"
3. Exit code: 0 if any succeeded, 1 if all failed

**AC-5.6: Retry Failed Executions**
1. When I run `rgrid retry --batch batch_abc123 --failed-only`, CLI retries only failed executions
2. Successful executions are skipped
3. New batch ID created for retry

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-5.1 | Services: Batch Expander | cli/batch/expander.py | Create 10 CSV files, run --batch *.csv, verify 10 executions submitted |
| AC-5.2 | Services: Batch Executor | cli/batch/executor.py | Mock API, submit 100 files with --parallel 20, verify max 20 concurrent |
| AC-5.3 | Services: Progress Tracker | cli/batch/progress.py | Mock API status, verify progress bar updates, check ETA calculation |
| AC-5.4 | Services: Output Organizer | cli/batch/outputs.py | Complete batch, verify outputs in ./outputs/input1/, ./outputs/input2/ |
| AC-5.5 | Workflows: Batch Execution | End-to-end test | Submit batch with 10 files, make 2 fail, verify 8 succeed and 2 reported |
| AC-5.6 | Services: Retry Handler | cli/commands/retry.py | Complete batch with failures, run retry --failed-only, verify only failed retried |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Large batches (10,000+ files) could exhaust database connections during submission
   - **Mitigation**: Connection pooling, rate limiting (max 100 submissions/second)
2. **R2**: Glob expansion could match unintended files (e.g., `**/*.csv` matches entire filesystem)
   - **Mitigation**: CLI warns if >1000 files matched, asks for confirmation
3. **R3**: Progress polling creates API load (100 users × 1 poll/2s = 50 req/s)
   - **Mitigation**: Acceptable for MVP, Epic 8 upgrades to WebSocket (push-based)

**Assumptions:**
1. **A1**: Users run batches from project directory (glob patterns are relative)
2. **A2**: Output files fit in local disk (no streaming download in Epic 5)
3. **A3**: Batch size <10,000 files for MVP (larger batches deferred to post-MVP)
4. **A4**: All files in batch use same script and runtime (no per-file customization)

**Open Questions:**
1. **Q1**: Should we support multiple glob patterns in one batch (e.g., `--batch data/*.csv inputs/*.json`)?
   - **Decision**: Deferred, use separate batches for different patterns in MVP
2. **Q2**: How to handle batch timeout (e.g., batch running for 24+ hours)?
   - **Decision**: No batch-level timeout in MVP (individual execution timeouts in Epic 8)
3. **Q3**: Should batch progress be stored in database for recovery?
   - **Decision**: No, progress computed on-demand from execution statuses (stateless)

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Glob expansion: Test various patterns (*.csv, **/*.json, data/{1..10}.txt)
   - Concurrency control: Verify semaphore limits parallelism
   - Progress calculation: Test ETA with various completion rates

2. **Integration Tests**
   - Batch submission: Submit 100-file batch, verify all executions created
   - Batch status: Query status, verify aggregation correct
   - Output organization: Download batch outputs, verify directory structure

3. **End-to-End Tests**
   - Complete batch flow: Submit → execute → download outputs
   - Batch with failures: 10 files, 2 fail, verify 8 outputs downloaded
   - Batch retry: Retry failed files, verify only failed re-executed

**Frameworks:**
- **Glob testing**: Create temp directory with test files
- **Progress tracking**: Mock API client, simulate status changes
- **Output organization**: Create temp outputs, verify structure

**Coverage of ACs:**
- AC-5.1: Unit test (glob expansion), E2E test (real batch)
- AC-5.2: Unit test (semaphore), integration test (mock API)
- AC-5.3: Unit test (progress math), integration test (mock status updates)
- AC-5.4: Integration test (download outputs, check directories)
- AC-5.5: E2E test (batch with intentional failures)
- AC-5.6: Integration test (create batch, fail some, retry)

**Edge Cases:**
- Glob pattern matches 0 files (error before submission)
- Glob pattern matches 100,000 files (warn user, ask confirmation)
- All executions fail (batch status=failed)
- Batch interrupted mid-submission (CLI crashes, partial batch created)
- Retry batch with 0 failures (no-op)

**Performance Tests:**
- Batch submission time: 1000 files, measure total submission time
- Progress polling overhead: Measure query time with 10,000 executions
- Output download time: 100 files × 10 MB, measure total download time

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 5.1
