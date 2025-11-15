# RGrid – Worker Node Model

- Provider: Hetzner Cloud.
- Type: CX22 (2 vCPU, 4GB RAM).
- Node lifetime: ~60 minutes max, plus idle timeout.
- Node runs multiple jobs (2 concurrent, 1 per vCPU).
- Node has no persistent state; everything job-related lives in Postgres + MinIO.

Node metadata:
- `provider_id` (Hetzner ID), `account_id`, `project_id`, `status`, `created_at`, `last_heartbeat`.

Failure handling:
- If node stops heartbeating, orchestrator marks it dead, requeues running jobs, and destroys the VM.
