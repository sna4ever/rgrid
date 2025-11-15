# RGrid – Architecture

Components:
- API (FastAPI): validates JobSpec, authenticates via Clerk, talks to Postgres and MinIO.
- Orchestrator: async service that watches queue depth, manages Hetzner nodes, enforces node lifetimes.
- Runner: agent process on each node that claims jobs, runs Docker, uploads artifacts, sends heartbeats.
- Storage: MinIO S3-compatible cluster for artifacts and (optionally) uploaded inputs.
- Database: Postgres for jobs, executions, logs, artifacts, nodes, heartbeats, costs.

High-level flow:
1. Client submits JobSpec → API stores job in Postgres (`status=queued`).
2. Orchestrator sees backlog, spawns CX22 worker nodes.
3. Runner on each node polls queue, claims job atomically, downloads inputs via presigned GET URLs.
4. Runner runs Docker container with command/args inside `/work/<job_id>`.
5. Runner uploads outputs via presigned PUT URLs to MinIO and records artifacts.
6. Job status and logs are visible via API/console; node is drained and destroyed after ~60 minutes.
