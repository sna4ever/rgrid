# RGrid – Backlog (Condensed)

## Phase 1 – Core Engine
- Set up Postgres schema (accounts, users, memberships, projects, jobs, executions, logs, artifacts, nodes, heartbeats, costs).
- Integrate Clerk in console + API (JWT verification).
- Implement JobSpec validation and job submission endpoint.
- Implement basic queue operations and job claiming.
- Build runner agent (claim job, download inputs, run Docker, upload outputs, send logs).

## Phase 2 – Autoscaling & Console
- Implement orchestrator autoscaler and node lifecycle.
- Add node registration and heartbeat reporting.
- Implement console pages for projects, jobs, logs, artifacts.
- Provide API keys for CI/server-to-server usage.

## Phase 3 – Production Hardening
- Cost tracking and usage limits per plan.
- Webhooks, better metrics, alerting.
- Support private container registries.
- Improve security (seccomp, stricter resource policies).
