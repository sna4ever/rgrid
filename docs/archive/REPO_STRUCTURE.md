# RGrid – Repo Structure (Condensed)

Recommended monorepo layout:

- `docs/` – all .md docs (this bundle).
- `api/` – FastAPI backend.
- `orchestrator/` – autoscaler and node lifecycle daemon.
- `runner/` – worker agent.
- `website/` – Next.js marketing website (rgrid.dev).
- `console/` – Next.js authenticated dashboard (app.rgrid.dev).
- `cli/` – Python-based `rgrid` CLI tool.
- `rgrid_common/` – Shared Python code (Money class, types, utils).
- `infra/` – Docker Compose, Nginx config, cloud-init templates, Terraform.
- `tests/` – unit and integration tests.
