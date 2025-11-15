# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RGrid is a distributed compute platform for running short-lived, containerized jobs on ephemeral Hetzner CX22 nodes. It provides elastic background compute for tasks like ffmpeg processing, Python scripts, LLM agents, and ETL without managing Kubernetes.

**Core workflow:**
1. Client submits JobSpec (declarative JSON) → API stores in Postgres queue
2. Orchestrator provisions Hetzner nodes on demand based on queue depth
3. Runner on each node claims jobs atomically, downloads inputs, runs Docker containers
4. Outputs uploaded to MinIO S3, artifacts and logs accessible via API
5. Nodes are ephemeral (~60 min lifetime) for cost efficiency

## Architecture

The system consists of five main components:

- **API (FastAPI)**: Validates JobSpec, authenticates via Clerk OIDC, manages Postgres and MinIO
- **Orchestrator**: Async service that autoscales Hetzner nodes based on queue depth, enforces node lifetimes
- **Runner**: Agent process on each worker node that claims jobs, executes Docker containers, handles I/O
- **Storage (MinIO)**: S3-compatible cluster for artifacts and uploaded inputs
- **Database (Postgres)**: Job queue, executions, logs, artifacts, nodes, heartbeats, cost tracking

**Repo structure** (monorepo layout):
- `docs/` - Comprehensive architecture documentation
- `api/` - FastAPI backend
- `orchestrator/` - Autoscaler and node lifecycle daemon
- `runner/` - Worker agent
- `console/` - Next.js frontend
- `cli/` - Python-based rgrid CLI tool
- `infra/` - Terraform, cloud-init templates, Dockerfiles
- `tests/` - Unit and integration tests

## Key Technical Details

**Multi-tenancy**: Clerk-backed auth with accounts → projects → jobs hierarchy

**Queue mechanism**: Postgres-based with `FOR UPDATE SKIP LOCKED` for atomic job claiming

**Job isolation**: Containers run with no network by default, read-only root filesystem, cgroup resource limits

**Compute model**: Hetzner CX22 nodes (2 vCPU) run max 2 concurrent jobs (1 job per vCPU)

**Artifact handling**: Runner (not container) handles all uploads/downloads via MinIO presigned URLs

**JobSpec format**: Kubernetes-inspired declarative spec with runtime/image, command, env, resources, files (inputs/outputs), timeout, network flag

**Reliability**: Automatic retries, dead worker detection via heartbeat timeouts, job timeout enforcement

## Documentation

Full technical documentation in `docs/` directory. Key files:
- `PROJECT_BRIEF.md` - High-level overview
- `ARCHITECTURE.md` - Component descriptions and data flow
- `JOB_SPEC.md` - JobSpec format and examples
- `DB_QUEUE.md` - Database schema and atomic claim pattern
- `REQUIREMENTS.md` - Functional and non-functional requirements
- `DECISIONS.md` - Architecture decision records
- `IMPLEMENTATION_ROADMAP.md` - Development phases

See `docs/TABLE_OF_CONTENTS.md` for complete documentation index.
