# RGrid – JobSpec v1

JobSpec is a JSON document describing how to run a job.

Example (ffmpeg thumbnail):

```json
{
  "apiVersion": "rgrid.dev/v1",
  "kind": "Job",
  "metadata": {
    "name": "thumb-001",
    "project": "image-pipeline"
  },
  "spec": {
    "runtime": "ffmpeg:latest",
    "command": ["ffmpeg", "-y", "-i", "input.png", "-vf", "scale=320:-1", "thumb.jpg"],
    "files": {
      "inputs": [
        {"path": "input.png", "url": "<PRESIGNED-GET-URL>"}
      ],
      "outputs": [
        {"path": "thumb.jpg", "type": "file"}
      ]
    },
    "resources": {
      "cpu": "1",
      "memory": "512Mi"
    },
    "timeoutSeconds": 60,
    "network": false,
    "retries": 1
  }
}
```

Key fields in `spec`:
- `runtime`: Docker image to run.
- `command` + `args`: what to execute.
- `env`: environment variables.
- `code`: optional inline Python code.
- `requirements`: Python deps (for Python jobs).
- `files.inputs`: list of (path, url) to download before run.
- `files.outputs`: list of (path, type) to upload after run.
- `resources`: CPU/memory limits per job.
- `timeoutSeconds`: max execution time.
- `network`: allow/deny outbound network.

## Input File Workflow

Users have two options for providing input files:

**Option 1: Upload to RGrid (recommended for most users)**
1. Call `POST /projects/:slug/files/upload` with file content
2. API uploads to MinIO and returns presigned GET URL (30-120 min expiry)
3. Use returned URL in `files.inputs[].url`

**Option 2: Bring Your Own Storage (BYO)**
1. Upload files to your own S3-compatible storage
2. Generate presigned GET URL from your bucket
3. Use your URL in `files.inputs[].url`

Both workflows use the same JobSpec format—RGrid runners download inputs via HTTPS presigned URLs regardless of source.
