# Epic Technical Specification: File & Artifact Management

Date: 2025-11-15
Author: BMad
Epic ID: 7
Status: Draft

---

## Overview

Epic 7 completes the file I/O lifecycle, making uploads and downloads completely automatic and invisible to users. Building on Epic 2's basic file handling, this epic implements comprehensive artifact management with automatic input upload detection, output collection, MinIO retention policies, auto-download for single executions, selective download controls, and streaming for large files.

The implementation ensures that remote execution feels identical to local execution from a file handling perspective - scripts receive input files as expected, outputs "just appear" locally after completion, and large file transfers (>100MB) are handled efficiently with streaming and compression. This epic delivers on the "files just work" promise.

## Objectives and Scope

**In Scope:**
- Automatic detection and upload of file arguments (referenced in script args)
- Comprehensive output collection (all files in /work directory)
- MinIO storage with 30-day retention policy
- Automatic output download to current directory (single executions)
- `--remote-only` flag to skip auto-download (keep outputs in cloud only)
- `rgrid outputs <exec_id>` command to list outputs before downloading
- `rgrid download <exec_id>` command for explicit download
- Large file optimization (>100MB): streaming upload/download, gzip compression
- Artifact metadata tracking (filename, size, content_type, S3 path)

**Out of Scope:**
- Incremental file uploads (rsync-style delta uploads)
- File versioning (multiple versions of same output)
- Encrypted file storage (MinIO encryption deferred to post-MVP)
- Direct S3 access for users (all via presigned URLs)
- Output file preview (Epic 10 web console feature)

## System Architecture Alignment

**Components Involved:**
- **CLI (cli/)**: File detection, upload, download, progress display
- **API (api/)**: Presigned URL generation, artifact metadata management
- **Runner (runner/)**: Output collection, upload to MinIO
- **Storage (MinIO)**: S3-compatible object storage with lifecycle policies
- **Database (Postgres)**: Artifact records (metadata, retention)

**Architecture Constraints:**
- Runner handles all uploads/downloads (containers never access MinIO directly)
- Presigned URLs expire after 1 hour (re-generate if needed)
- MinIO bucket: `rgrid-executions`
- Object keys: `executions/{exec_id}/inputs/{filename}` and `outputs/{filename}`
- Retention: 30 days (configurable via environment variable)
- Large file threshold: 100 MB (streaming + compression)

**Cross-Epic Dependencies:**
- Requires Epic 1: API infrastructure, MinIO setup
- Requires Epic 2: Basic execution flow, initial file handling
- Leverages Epic 5: Batch outputs organized by input filename
- Optimized by Epic 6: Input caching reduces uploads

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **CLI File Detector** (`cli/rgrid/files/detector.py`) | Detect file arguments in command line | Script args list | File paths to upload | CLI Team |
| **CLI Upload Manager** (`cli/rgrid/files/uploader.py`) | Upload files with progress, streaming for large files | File paths, presigned URLs | Upload completion status | CLI Team |
| **API Storage Service** (`api/services/storage.py`) | Generate presigned URLs for MinIO | File paths, operation (PUT/GET) | Presigned URLs (1-hour TTL) | API Team |
| **Runner Output Collector** (`runner/output_collector.py`) | Scan /work directory, upload all outputs | Execution ID, /work path | Artifact records | Runner Team |
| **CLI Download Manager** (`cli/rgrid/files/downloader.py`) | Download outputs with progress, decompress if needed | Execution ID, output directory | Downloaded file paths | CLI Team |
| **CLI Outputs Lister** (`cli/rgrid/commands/outputs.py`) | List available outputs for execution | Execution ID | Artifact list (filename, size) | CLI Team |
| **MinIO Lifecycle Manager** (`infra/minio/lifecycle.py`) | Configure bucket retention policy | Retention days (30) | Lifecycle rule ID | Infra Team |

### Data Models and Contracts

**Artifact Record (Postgres `artifacts` table - Extended from Epic 2):**
```python
class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: str           # Primary key, format: artifact_{uuid}
    execution_id: str          # Foreign key to executions
    artifact_type: str         # "input" | "output"

    filename: str              # Original filename (e.g., "data.csv")
    file_path: str             # MinIO object key (e.g., "executions/exec_abc/inputs/data.csv")
    size_bytes: int            # File size in bytes
    content_type: str          # MIME type (e.g., "text/csv", "image/png")

    # Epic 7 additions:
    compressed: bool           # True if file is gzip-compressed in MinIO
    original_size_bytes: int   # Uncompressed size (if compressed)
    checksum_sha256: str       # SHA256 hash for integrity verification

    created_at: datetime       # Upload timestamp
    expires_at: datetime       # Retention expiry (created_at + 30 days)
```

**Presigned URL Response:**
```python
# GET /api/v1/executions/{exec_id}/presigned-urls?operation=put&files=data.csv,config.json
class PresignedURLResponse(BaseModel):
    urls: Dict[str, str]       # {filename: presigned_url}
    expires_at: datetime       # URL expiration time (1 hour from now)

# Example:
{
  "urls": {
    "data.csv": "https://minio:9000/rgrid-executions/executions/exec_abc/inputs/data.csv?X-Amz-Algorithm=...",
    "config.json": "https://minio:9000/rgrid-executions/executions/exec_abc/inputs/config.json?X-Amz-..."
  },
  "expires_at": "2025-11-15T11:30:00Z"
}
```

**Output List Response:**
```python
# GET /api/v1/executions/{exec_id}/outputs
class OutputListResponse(BaseModel):
    execution_id: str
    outputs: List[ArtifactMetadata]
    total_size_bytes: int      # Sum of all output sizes

class ArtifactMetadata(BaseModel):
    filename: str
    size_bytes: int
    content_type: str
    compressed: bool
    created_at: datetime
```

### APIs and Interfaces

**CLI File Detection:**
```python
# cli/rgrid/files/detector.py
def detect_file_arguments(args: List[str]) -> List[Path]:
    """
    Detect which arguments are file paths that need uploading.

    Strategy:
    1. Check if arg is a valid path: os.path.exists(arg)
    2. Check if path is a file (not directory): os.path.isfile(arg)
    3. Exclude script itself (first arg)

    Args:
        args: Script arguments (e.g., ["data.csv", "output_dir", "--flag"])

    Returns:
        List of Path objects that are files

    Example:
        >>> detect_file_arguments(["data.csv", "output/", "--verbose"])
        [Path("data.csv")]  # output/ is directory, --verbose is flag
    """
    files = []
    for arg in args:
        path = Path(arg)
        if path.exists() and path.is_file():
            files.append(path)
    return files
```

**CLI Upload with Progress:**
```python
# cli/rgrid/files/uploader.py
async def upload_files(
    files: List[Path],
    presigned_urls: Dict[str, str],
    show_progress: bool = True
) -> Dict[str, str]:
    """
    Upload files to MinIO using presigned URLs.

    Features:
    - Parallel uploads (asyncio)
    - Progress bar for each file (rich library)
    - Streaming for large files (>100MB)
    - Gzip compression for text files >100MB

    Args:
        files: List of file paths to upload
        presigned_urls: Map of filename → presigned PUT URL
        show_progress: Display progress bars

    Returns:
        Map of filename → MinIO object key
    """
    tasks = []
    for file_path in files:
        url = presigned_urls[file_path.name]
        task = upload_single_file(file_path, url, show_progress)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return {f.name: r for f, r in zip(files, results)}

async def upload_single_file(file_path: Path, url: str, show_progress: bool) -> str:
    """
    Upload single file with streaming for large files.
    """
    size = file_path.stat().st_size

    # Streaming for large files (>100MB)
    if size > 100 * 1024 * 1024:  # 100 MB
        # Check if text file (compress with gzip)
        is_text = is_text_file(file_path)
        if is_text:
            return await upload_compressed(file_path, url, show_progress)
        else:
            return await upload_streaming(file_path, url, show_progress)
    else:
        # Small file: load into memory and PUT
        content = file_path.read_bytes()
        async with httpx.AsyncClient() as client:
            response = await client.put(url, content=content)
            response.raise_for_status()
        return file_path.name
```

**Runner Output Collection:**
```python
# runner/output_collector.py
async def collect_and_upload_outputs(execution_id: str, work_dir: Path) -> List[str]:
    """
    Collect all files in /work directory and upload to MinIO.

    Algorithm:
    1. Scan /work for all files (exclude script.py, inputs/)
    2. For each file:
       a. Calculate SHA256 checksum
       b. Determine content type (MIME)
       c. Get presigned PUT URL from API
       d. Upload file (streaming if >100MB, compress if text)
       e. Create artifact record via API
    3. Return list of artifact IDs

    Args:
        execution_id: Execution ID
        work_dir: Container /work directory path

    Returns:
        List of artifact IDs created
    """
    output_files = []
    for file_path in work_dir.rglob("*"):
        # Exclude script and inputs
        if file_path.name == "script.py" or "inputs" in file_path.parts:
            continue

        if file_path.is_file():
            output_files.append(file_path)

    logger.info(f"Found {len(output_files)} output files for {execution_id}")

    artifact_ids = []
    for file_path in output_files:
        # Calculate metadata
        size = file_path.stat().st_size
        checksum = calculate_sha256(file_path)
        content_type = guess_mime_type(file_path)

        # Get presigned URL
        presigned_url = await api_client.get_presigned_url(
            execution_id=execution_id,
            filename=file_path.name,
            operation="put",
            artifact_type="output"
        )

        # Upload (streaming if large)
        if size > 100 * 1024 * 1024:
            await upload_streaming(file_path, presigned_url)
        else:
            await upload_direct(file_path, presigned_url)

        # Create artifact record
        artifact_id = await api_client.create_artifact(
            execution_id=execution_id,
            filename=file_path.name,
            size_bytes=size,
            content_type=content_type,
            checksum_sha256=checksum,
            artifact_type="output"
        )

        artifact_ids.append(artifact_id)

    return artifact_ids
```

**CLI Auto-Download (Single Execution):**
```python
# cli/rgrid/commands/run.py (updated for Epic 7)
async def run_script(script: Path, args: List[str], remote_only: bool = False, ...):
    """
    Execute script and auto-download outputs (unless --remote-only).
    """
    # Submit execution (Epic 2 logic)
    execution_id = await submit_execution(script, args, ...)

    # Wait for completion (polling or --watch, Epic 8 adds WebSocket)
    await wait_for_completion(execution_id)

    # Auto-download outputs (unless --remote-only)
    if not remote_only:
        print(f"Downloading outputs from {execution_id}...")
        downloaded = await download_outputs(execution_id, output_dir=Path.cwd())
        print(f"✓ Downloaded {len(downloaded)} files:")
        for file in downloaded:
            print(f"  - {file.name} ({format_size(file.stat().st_size)})")
    else:
        print(f"✓ Execution complete. Outputs stored remotely.")
        print(f"  Download with: rgrid download {execution_id}")
```

**CLI Download Manager:**
```python
# cli/rgrid/files/downloader.py
async def download_outputs(
    execution_id: str,
    output_dir: Path,
    decompress: bool = True
) -> List[Path]:
    """
    Download all outputs for execution.

    Args:
        execution_id: Execution ID
        output_dir: Local directory to save outputs
        decompress: Automatically decompress gzipped files

    Returns:
        List of downloaded file paths
    """
    # Get artifact list from API
    artifacts = await api_client.list_outputs(execution_id)

    print(f"Downloading {len(artifacts)} files...")

    # Download in parallel
    tasks = []
    for artifact in artifacts:
        task = download_single_artifact(artifact, output_dir, decompress)
        tasks.append(task)

    downloaded_paths = await asyncio.gather(*tasks)
    return downloaded_paths

async def download_single_artifact(
    artifact: ArtifactMetadata,
    output_dir: Path,
    decompress: bool
) -> Path:
    """
    Download single artifact with streaming for large files.
    """
    # Get presigned GET URL
    presigned_url = await api_client.get_presigned_url(
        execution_id=artifact.execution_id,
        filename=artifact.filename,
        operation="get"
    )

    output_path = output_dir / artifact.filename

    # Streaming download for large files
    if artifact.size_bytes > 100 * 1024 * 1024:
        await download_streaming(presigned_url, output_path, decompress)
    else:
        # Small file: load into memory
        async with httpx.AsyncClient() as client:
            response = await client.get(presigned_url)
            response.raise_for_status()

            content = response.content
            if decompress and artifact.compressed:
                content = gzip.decompress(content)

            output_path.write_bytes(content)

    return output_path
```

**MinIO Retention Policy:**
```python
# infra/minio/lifecycle.py
from minio import Minio
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

def configure_retention_policy(bucket_name: str, retention_days: int = 30):
    """
    Configure MinIO bucket lifecycle policy for automatic deletion.

    Args:
        bucket_name: Bucket name (e.g., "rgrid-executions")
        retention_days: Days to retain objects (default 30)
    """
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY
    )

    # Define lifecycle rule
    rule = Rule(
        rule_id="delete-old-artifacts",
        rule_filter=None,  # Apply to all objects
        status="Enabled",
        expiration=Expiration(days=retention_days)
    )

    lifecycle_config = LifecycleConfig([rule])

    # Apply to bucket
    client.set_bucket_lifecycle(bucket_name, lifecycle_config)

    logger.info(f"Set {bucket_name} retention: {retention_days} days")
```

### Workflows and Sequencing

**Complete File Lifecycle (Single Execution with Inputs/Outputs):**
```
1. USER: rgrid run process.py data.csv --env API_KEY=abc

2. CLI FILE DETECTOR:
   a. Parse args: ["data.csv"]
   b. Check os.path.exists("data.csv") → True
   c. Check os.path.isfile("data.csv") → True
   d. Detect: data.csv needs upload

3. CLI → API: Request Presigned Upload URLs
   a. POST /api/v1/executions (with input_files=["data.csv"])
   b. API generates presigned PUT URL for executions/{exec_id}/inputs/data.csv
   c. API returns: {urls: {"data.csv": "https://minio:9000/..."}}

4. CLI UPLOAD MANAGER:
   a. Upload data.csv to presigned URL
   b. Display progress: "Uploading data.csv [====>    ] 60% (600 KB/1 MB)"
   c. Upload complete (1 second for 1 MB file)

5. RUNNER EXECUTION:
   a. Download data.csv from MinIO to /work/inputs/data.csv
   b. Run script: python /work/script.py /work/inputs/data.csv
   c. Script creates outputs: /work/output.json, /work/results.csv

6. RUNNER OUTPUT COLLECTOR:
   a. Scan /work directory:
      - output.json (500 KB)
      - results.csv (2 MB)
   b. Calculate checksums (SHA256)
   c. Get presigned PUT URLs from API
   d. Upload outputs to executions/{exec_id}/outputs/
   e. Create artifact records:
      - artifact_id=artifact_1, filename=output.json, size=500KB
      - artifact_id=artifact_2, filename=results.csv, size=2MB

7. API: Update Execution
   a. Set status=completed
   b. Record artifact count: 2 outputs

8. CLI AUTO-DOWNLOAD (unless --remote-only):
   a. Query API: GET /api/v1/executions/{exec_id}/outputs
   b. Response: [{filename: "output.json", size: 500000}, ...]
   c. Get presigned GET URLs
   d. Download files to current directory:
      - ./output.json
      - ./results.csv
   e. Display: "✓ Downloaded 2 files: output.json (500 KB), results.csv (2 MB)"

9. USER: ls
   output.json  results.csv  (files appear as if executed locally!)
```

**Large File Workflow (>100MB with Compression):**
```
1. USER: rgrid run process.py --batch large_files/*.txt (each 500 MB text file)

2. CLI UPLOAD (per file):
   a. Detect file size: 500 MB
   b. Check is_text_file: True (*.txt)
   c. Compress with gzip: 500 MB → 50 MB (10:1 compression for text)
   d. Stream upload in chunks (10 MB chunks, 5 chunks total)
   e. Display: "Uploading large_file1.txt.gz [====>    ] 60% (30 MB/50 MB)"
   f. Total upload time: ~5 seconds (50 MB @ 10 MB/s)

3. API: Create Artifact
   a. Record: compressed=True, original_size=500MB, size=50MB

4. RUNNER:
   a. Download compressed file: 50 MB (5 seconds)
   b. Decompress: 50 MB → 500 MB (in memory stream, fast)
   c. Execute script with decompressed file

5. RUNNER OUTPUT (script creates 200 MB CSV):
   a. Detect output size: 200 MB
   b. Check is_text: True (*.csv)
   c. Compress: 200 MB → 20 MB
   d. Stream upload: 20 MB (~2 seconds)

6. CLI AUTO-DOWNLOAD:
   a. Download compressed: 20 MB
   b. Decompress automatically: 20 MB → 200 MB
   c. Save uncompressed file: ./output.csv (200 MB)
   d. Total download time: ~2 seconds

Performance: 500 MB upload + 200 MB download = ~7 seconds (vs. 70 seconds uncompressed)
```

**Retention Policy Enforcement:**
```
# MinIO Lifecycle Manager (runs daily, configured once at startup)

1. MINIO: Daily Cleanup Job (automatic)
   a. Scan bucket: rgrid-executions
   b. Find objects older than 30 days (based on created_at metadata)
   c. Delete: executions/exec_old/inputs/*, executions/exec_old/outputs/*
   d. Objects deleted: 500 files, 10 GB freed

2. DATABASE: Artifact Cleanup (orchestrator cron job)
   a. SELECT artifacts WHERE expires_at < NOW()
   b. Mark artifacts as expired (or delete records)
   c. Log: "Cleaned up 500 expired artifacts"

Note: MinIO deletes objects automatically, database cleanup is for metadata consistency
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Upload throughput**: 10 MB/s minimum (limited by network, not application)
- **Download throughput**: 10 MB/s minimum
- **Large file compression**: 10:1 ratio for text files (varies by content)
- **Streaming overhead**: < 5% (chunk size: 10 MB)
- **Presigned URL generation**: < 50ms per URL
- **File detection**: < 100ms for 100 arguments

**Scalability:**
- Support files up to 5 GB (practical limit for MVP)
- Parallel uploads: 10 files concurrently (CLI)
- MinIO bucket: Unlimited objects (scales horizontally)

**Source:** Architecture performance targets

### Security

**Access Control:**
- Presigned URLs expire after 1 hour (minimize exposure window)
- URLs are one-time use for uploads (cannot reuse for different execution)
- MinIO access restricted to API and runner (no direct user access)

**Data Integrity:**
- SHA256 checksums verify file integrity (detect corruption)
- Checksums stored in artifacts table for post-download verification

**Source:** Architecture security decisions

### Reliability/Availability

**Fault Tolerance:**
- **Upload failures**: CLI retries with exponential backoff (max 3 retries)
- **Download failures**: CLI retries, resume partial downloads (future enhancement)
- **Presigned URL expiration**: Re-generate URL if expired mid-operation
- **MinIO unavailable**: API returns 503, CLI displays error (fail fast)

**Data Retention:**
- 30-day retention ensures recent artifacts available
- Users responsible for downloading before expiry (warning in CLI)
- Expired artifacts logged but not recoverable (no soft delete)

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Upload/download throughput (MB/s)
- Large file compression ratio (compressed / original)
- Artifact count by type (input, output)
- Total storage used (MB)
- Retention cleanup count (artifacts deleted per day)

**Logging:**
- CLI: Upload/download progress, file sizes
- API: Presigned URL generation, artifact creation
- MinIO: Object lifecycle events (deletion logs)

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Python Dependencies:**
```toml
# cli/pyproject.toml
[tool.poetry.dependencies]
httpx = "^0.25.0"         # Streaming upload/download
python-magic = "^0.4.27"  # MIME type detection
rich = "^13.7.0"          # Progress bars

# api/pyproject.toml
[tool.poetry.dependencies]
boto3 = "^1.29.0"         # MinIO S3 client (presigned URLs)

# runner/pyproject.toml
[tool.poetry.dependencies]
boto3 = "^1.29.0"         # MinIO client for uploads
```

**MinIO Configuration:**
```yaml
# infra/minio/config.yaml
bucket_name: rgrid-executions
region: us-east-1  # Default MinIO region
retention_days: 30
lifecycle_enabled: true

# MinIO credentials (environment variables)
MINIO_ENDPOINT: minio:9000
MINIO_ACCESS_KEY: <secret>
MINIO_SECRET_KEY: <secret>
```

**Database Schema Updates:**
```sql
-- Update artifacts table (Epic 7 additions)
ALTER TABLE artifacts ADD COLUMN compressed BOOLEAN DEFAULT false;
ALTER TABLE artifacts ADD COLUMN original_size_bytes BIGINT;
ALTER TABLE artifacts ADD COLUMN checksum_sha256 VARCHAR(64);
ALTER TABLE artifacts ADD COLUMN expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days';

-- Index for retention cleanup
CREATE INDEX idx_artifacts_expires_at ON artifacts(expires_at);
```

## Acceptance Criteria (Authoritative)

**AC-7.1: Auto-Upload Input Files**
1. When script arguments reference files (detected via os.path.exists), CLI uploads files to MinIO
2. Runner downloads files into container /work directory
3. Script receives file paths as arguments

**AC-7.2: Auto-Collect Output Files**
1. All files created in /work directory are collected after script completion
2. Files uploaded to MinIO under executions/{exec_id}/outputs/
3. Artifact records created with filename, size, content_type

**AC-7.3: MinIO Retention Policy**
1. MinIO bucket configured with 30-day lifecycle policy
2. Objects older than 30 days automatically deleted
3. Artifacts table expires_at field set to created_at + 30 days

**AC-7.4: Auto-Download Outputs (Single Execution)**
1. After single execution completes, CLI downloads outputs to current directory
2. Files appear locally as if script ran locally
3. CLI displays: "✓ Downloaded N files: file1 (size), file2 (size)"

**AC-7.5: --remote-only Flag**
1. With `--remote-only`, CLI skips auto-download
2. CLI displays: "Outputs stored remotely. Download with: rgrid download {exec_id}"
3. Outputs remain in MinIO until explicit download

**AC-7.6: Large File Streaming and Compression**
1. Files >100MB uploaded/downloaded with streaming (chunked)
2. Text files >100MB compressed with gzip before upload
3. Downloads automatically decompress gzipped files

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-7.1 | Services: Upload Manager | cli/files/uploader.py | Run with file arg, verify uploaded to MinIO, check artifact record |
| AC-7.2 | Services: Output Collector | runner/output_collector.py | Script creates 2 files, verify both uploaded and recorded |
| AC-7.3 | Services: Lifecycle Manager | infra/minio/lifecycle.py | Configure policy, create object with old timestamp, verify deleted |
| AC-7.4 | Services: Download Manager | cli/files/downloader.py | Complete execution, verify outputs downloaded to current directory |
| AC-7.5 | CLI: run command | cli/commands/run.py | Run with --remote-only, verify no download, check files in MinIO |
| AC-7.6 | Services: Upload/Download | cli/files/uploader.py | Upload 200MB file, verify compressed, download, verify decompressed |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Large file uploads (>1GB) could timeout on slow networks
   - **Mitigation**: Streaming with chunking, retry failed chunks (future: resumable uploads)
2. **R2**: Presigned URLs expire mid-upload/download (1-hour TTL)
   - **Mitigation**: Re-generate URL if expired, retry operation
3. **R3**: Gzip compression may not help binary files (images, videos)
   - **Mitigation**: Detect file type, only compress text files

**Assumptions:**
1. **A1**: Users have sufficient disk space for downloads (no quota checking)
2. **A2**: Network bandwidth supports 10 MB/s sustained (reasonable for cloud)
3. **A3**: 30-day retention sufficient (most use cases download within days)
4. **A4**: File paths in args are relative to current directory (no absolute paths)

**Open Questions:**
1. **Q1**: Should we support resumable uploads/downloads (for large files)?
   - **Decision**: Deferred to post-MVP (complex, requires multipart upload state)
2. **Q2**: Should users be able to extend retention beyond 30 days?
   - **Decision**: No in MVP (fixed 30 days), future: configurable per-execution
3. **Q3**: How to handle file name collisions (script creates file with same name)?
   - **Decision**: Last write wins (overwrite), or error if multiple outputs with same name

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - File detection: Test with various arg patterns, verify correct files detected
   - Presigned URL generation: Mock boto3, verify URL format
   - Compression: Test gzip compress/decompress, verify integrity

2. **Integration Tests**
   - Upload: Upload file to MinIO, verify object exists
   - Download: Download file from MinIO, verify content matches
   - Retention: Create object with old timestamp, verify lifecycle deletes

3. **End-to-End Tests**
   - Complete flow: Run with input file → execution → outputs downloaded
   - Large file: Upload/download 200MB file, verify streaming and compression
   - Batch outputs: Verify outputs organized by input filename (Epic 5 integration)

**Frameworks:**
- **MinIO**: minio-py client, local MinIO testcontainer
- **File I/O**: Python tempfile for test files
- **Progress bars**: Mock rich.progress for unit tests

**Coverage of ACs:**
- AC-7.1: Integration test (upload to MinIO, check object)
- AC-7.2: E2E test (script creates files, verify uploaded)
- AC-7.3: Integration test (configure lifecycle, verify deletion)
- AC-7.4: E2E test (complete execution, check files downloaded)
- AC-7.5: E2E test (run with --remote-only, verify no download)
- AC-7.6: Integration test (upload large file, verify compressed, download, verify decompressed)

**Edge Cases:**
- Script creates 0 outputs (no artifacts, valid)
- Script creates 1000 outputs (all uploaded, performance test)
- Upload fails mid-stream (retry, verify integrity)
- Download fails mid-stream (retry)
- File with non-ASCII filename (UTF-8 encoding)
- Presigned URL expires during upload (re-generate, retry)

**Performance Tests:**
- Upload 1 GB file: Measure throughput (target: 10 MB/s)
- Download 1 GB file: Measure throughput
- Compression ratio: 100 MB text file (target: 10:1 ratio)

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 7.1
