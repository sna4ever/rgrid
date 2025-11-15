# RGrid – Storage Pipeline (Condensed)

Inputs:
- Defined in JobSpec as `files.inputs[] = {path, url}`.
- Runner downloads them to `/work/<job_id>/<path>` via presigned GET URLs.

Outputs:
- Defined in JobSpec as `files.outputs[] = {path, type}`.
- After container exits, runner checks these paths under `/work/<job_id>`.
- For each existing file, API issues presigned PUT URL.
- Runner uploads to MinIO; API stores artifact metadata (path, size, MIME type, storage key).

Layout:
- MinIO keys like `artifacts/<account>/<project>/<job>/<filename>`.

No credentials ever appear in containers; everything relies on short-lived presigned URLs.
