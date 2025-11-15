# RGrid – Sequence Flows (Condensed)

Example: Submit job → completion:

1. Client → API: POST /projects/:slug/jobs with JobSpec.
2. API → DB: INSERT job (status=queued).
3. Orchestrator sees queue depth, spawns nodes via Hetzner API.
4. Runner on node → API: register + claim job.
5. Runner → storage: download input via presigned GET.
6. Runner → Docker: run command.
7. Runner → storage: upload output via presigned PUT.
8. Runner → API: mark execution + job status.
9. Client → API: GET /jobs/:id or WebSocket for logs.

Also covers:
- Bulk ffmpeg thumbnails (300 jobs).
- Node drain and termination.
- Timeout and requeue scenarios.
