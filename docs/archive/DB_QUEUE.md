# RGrid – Database Queue Model (Condensed)

Core tables:
- `accounts`, `users`, `memberships`: multi-tenant identity mirror (Clerk-backed).
- `projects`: execution units that own jobs and API keys.
- `jobs`: JobSpec + status, retries, timestamps, cost, current_execution_id.
- `executions`: individual attempts to run a job (for retries).
- `job_logs`: line-buffered logs.
- `artifacts`: outputs stored in MinIO.
- `worker_nodes`, `heartbeats`: node tracking and health.

Atomic claim pattern (simplified):

```sql
WITH next_job AS (
  SELECT id
  FROM jobs
  WHERE status = 'queued'
  ORDER BY priority, created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs
SET status = 'running', started_at = now()
FROM next_job
WHERE jobs.id = next_job.id
RETURNING jobs.*;
```

**Note:** Jobs are claimed from a **global shared pool** across all projects. Nodes are not dedicated per project—any worker can claim any job. This enables maximum resource utilization and cost efficiency (core business value).

Retries: failed/abandoned jobs are set back to `queued` if `retries < max_retries`. Timeouts and missing heartbeats are used to detect dead jobs/nodes.
