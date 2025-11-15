# RGrid – Artifacts Model

Artifacts represent files produced by job executions.

Key fields:
- `id`, `execution_id`, `project_id`, `account_id`
- `path` (relative in container/workdir)
- `size_bytes`, `content_type`
- `created_at`

Downloads:
- Client calls `/jobs/:id/artifacts` to list.
- Then `/jobs/:id/artifacts/:artifact_id/download` to get a presigned GET URL.

Retention:
- Configurable per project (e.g. keep 30 days).
- Cleanup via periodic job that deletes older MinIO objects and DB rows.
