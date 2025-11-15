# RGrid – Project Brief

RGrid (rgrid.dev) is a distributed compute platform for running short-lived, containerized jobs
on ephemeral Hetzner CX22 nodes. It focuses on developer ergonomics, cost efficiency, and strong
isolation. Jobs are described declaratively via a JSON JobSpec, executed in Docker, and tracked
via a Postgres-backed queue.

Core ideas:
- You POST a JobSpec (runtime image, command, inputs, outputs, resources).
- RGrid provisions nodes on demand, runs jobs in isolated containers, uploads artifacts to MinIO.
- You query status, logs, and artifacts via a clean REST + WebSocket API.
- Access via CLI (primary), web console (monitoring), or marketing website (onboarding).

Target users: solo devs, SaaS builders, and teams needing elastic background compute (ffmpeg,
Python scripts, LLM agents, ETL, etc.) without running Kubernetes or managing their own workers.

**User-facing components:**
- **CLI** (`rgrid`) - Primary interface for developers
- **API** (api.rgrid.dev) - REST + WebSocket backend
- **Console** (app.rgrid.dev) - Authenticated dashboard for monitoring jobs, viewing logs, managing billing
- **Website** (rgrid.dev) - Public marketing site with landing page, features, pricing, docs
