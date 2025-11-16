# Dev 1 - Tier 3 Completion - Story 7-6 (FINAL)

## Git Setup (Run First)

```bash
cd /home/sune/Projects/rgrid
git checkout main
git pull origin main
git checkout -b story-7-6-large-file-streaming
```

## Task

Activate DEV (Amelia). Implement Story 7-6: Large File Streaming and Compression (FINAL TIER 3 STORY).

## Story Details

**Epic**: Epic 7 - File & Artifact Management
**Priority**: High (Tier 3 - Production-Ready)
**Estimate**: 6-8 hours
**Complexity**: Medium
**Risk**: Medium (memory management, streaming)

## Objective

Large files (>100MB) can exhaust memory if loaded entirely. Implement streaming uploads/downloads with gzip compression to handle multi-GB files efficiently. This completes Tier 3 file handling and enables production workloads with large datasets.

## Acceptance Criteria

- [ ] Files >100MB are streamed (not loaded into memory)
- [ ] Upload streaming uses chunked transfer encoding
- [ ] Download streaming uses chunked responses
- [ ] Files automatically compressed with gzip during upload
- [ ] Files automatically decompressed during download
- [ ] Memory usage stays constant regardless of file size
- [ ] Test with 500MB file: upload and download succeed
- [ ] Test with 2GB file: upload and download succeed
- [ ] CLI shows progress bar for large file transfers
- [ ] Error handling for partial transfers (resume/retry)

## Success Metric

```bash
# Create 500MB test file
dd if=/dev/zero of=large_test.dat bs=1M count=500

# Run script that processes large file
rgrid run process_large_file.py large_test.dat

# Verify:
# - Upload completes without memory spike
# - Download completes without memory spike
# - File integrity preserved (checksum matches)
# - Progress bar shows during transfer
```

## Files to Modify

- `cli/rgrid/upload.py` - Add streaming upload with compression
- `cli/rgrid/download.py` - Add streaming download with decompression
- `api/api/endpoints/artifacts.py` - Stream large files from MinIO
- `runner/runner/file_handler.py` - Stream files to/from container
- `cli/rgrid/progress.py` - NEW FILE - Progress bar for transfers
- `tests/unit/test_file_streaming.py` - NEW FILE - Unit tests
- `tests/integration/test_large_files.py` - NEW FILE - Integration tests (500MB+)

## Testing Strategy (TDD)

**Unit Tests** (tests/unit/test_file_streaming.py):
1. `test_stream_upload_chunks()` - Upload streams in chunks
2. `test_stream_download_chunks()` - Download streams in chunks
3. `test_gzip_compression()` - Files compressed correctly
4. `test_gzip_decompression()` - Files decompressed correctly
5. `test_memory_usage_constant()` - Memory doesn't grow with file size
6. `test_checksum_verification()` - File integrity preserved

**Integration Tests** (tests/integration/test_large_files.py):
1. `test_upload_500mb_file()` - 500MB file uploads successfully
2. `test_download_500mb_file()` - 500MB file downloads successfully
3. `test_round_trip_integrity()` - Upload + download preserves file
4. `test_progress_bar_display()` - Progress shows during transfer

**Expected Test Count**: 6 unit tests, 4 integration tests

## Implementation Hints

**Streaming upload** (cli/rgrid/upload.py):
```python
import gzip
import requests
from tqdm import tqdm

def upload_file_streaming(file_path: Path, presigned_url: str):
    """Upload file with streaming and compression."""
    file_size = file_path.stat().st_size

    # Stream with gzip compression
    with open(file_path, 'rb') as f_in:
        with tqdm(total=file_size, unit='B', unit_scale=True) as pbar:
            # Compress on the fly
            def compressed_chunks():
                compressor = gzip.compress
                chunk_size = 8192
                while chunk := f_in.read(chunk_size):
                    pbar.update(len(chunk))
                    yield compressor(chunk)

            response = requests.put(
                presigned_url,
                data=compressed_chunks(),
                headers={'Content-Encoding': 'gzip'}
            )

    return response.status_code == 200
```

**Streaming download** (cli/rgrid/download.py):
```python
import gzip
from tqdm import tqdm

def download_file_streaming(presigned_url: str, output_path: Path):
    """Download file with streaming and decompression."""
    response = requests.get(presigned_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(output_path, 'wb') as f_out:
        with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            # Decompress on the fly
            decompressor = gzip.GzipFile(fileobj=response.raw)

            while chunk := decompressor.read(8192):
                f_out.write(chunk)
                pbar.update(len(chunk))
```

**Memory-efficient approach**:
- Never load entire file into memory
- Use generators/iterators for chunks
- Process 8KB chunks at a time
- gzip compression reduces bandwidth by ~70%

**MinIO streaming** (api/endpoints/artifacts.py):
```python
from fastapi.responses import StreamingResponse

@router.get("/artifacts/{exec_id}/download/{filename}")
async def download_artifact(exec_id: str, filename: str):
    """Stream artifact from MinIO."""
    s3_key = f"executions/{exec_id}/outputs/{filename}"

    # MinIO streaming
    obj = minio_client.get_object(bucket, s3_key)

    def iterfile():
        """Stream file in chunks."""
        for chunk in obj.stream(8192):
            yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

## Story File

`docs/sprint-artifacts/stories/7-6-implement-large-file-streaming-and-compression.md`

## Dependencies

✅ Story 7-5 complete (--remote-only flag - Tier 5)
✅ Story 7-4 complete (Basic download - Tier 1)
✅ MinIO setup complete (Tier 1)

## Estimated Effort

6-8 hours (medium complexity, memory optimization, large file testing)

---

**Use TDD - write failing tests FIRST, then implement.**

---

## 🎯 REQUIRED: Story Completion Workflow

When development is complete, you MUST follow these steps:

### 1. Update Sprint Status

Edit `docs/sprint-artifacts/sprint-status.yaml`:
- Find your story line (7-6-implement-large-file-streaming-and-compression)
- Change status from `ready-for-dev` → `done`
- Add completion comment

Example:
```yaml
7-6-implement-large-file-streaming-and-compression: done  # Tier 3 - Dev 1 - COMPLETED 2025-11-16
```

### 2. Commit Your Work

```bash
git add .
git commit -m "Implement Story 7-6: Large File Streaming and Compression

- Stream files >100MB without loading into memory
- Automatic gzip compression/decompression
- Progress bar for large transfers
- Tested with 500MB and 2GB files
- Memory usage constant regardless of file size
- All acceptance criteria met
- 6 unit tests passing
- 4 integration tests passing (including 500MB file test)
- TIER 3 NOW 100% COMPLETE

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Merge to Main

```bash
git checkout main
git pull origin main
git merge story-7-6-large-file-streaming
```

### 4. Push to Remote

```bash
git push origin main
```

### 5. Confirm Completion

Reply to user: **"Story 7-6 merged and complete - TIER 3 IS NOW 100% DONE"**

---

**⚠️ CRITICAL**: Do NOT say "ready for review" or "ask me anything" without completing these steps first. The story is NOT done until it's merged to main.

---

## 🎉 TIER 3 MILESTONE

After this story is complete:
- **Tier 3: Production-Ready** will be 100% complete (8/8 stories)
- RGrid will have production-grade reliability, resource limits, timeouts, migrations, and file handling
- Ready to deploy to staging environment for real-world testing
- Ready to begin Tier 4: Distributed Cloud (Ray + Hetzner)
