# Story 1.1: Initialize Monorepo Project Structure

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.1
**Status:** drafted
**Prerequisites:** None (first story)

## User Story

As a developer,
I want a properly structured monorepo with all components organized logically,
So that I can develop API, orchestrator, runner, CLI, and web apps in a cohesive codebase.

## Acceptance Criteria

**Given** a fresh development environment
**When** the project is initialized
**Then** the directory structure follows the architecture:
- `api/` - FastAPI backend with routes/, services/, schemas/, models/
- `orchestrator/` - Autoscaler service with provisioning logic
- `runner/` - Worker agent with Docker execution
- `cli/` - Python CLI tool with Click framework
- `console/` - Next.js dashboard (App Router)
- `website/` - Next.js marketing site
- `common/` - Shared Python package for models/schemas
- `infra/` - Terraform, cloud-init, Dockerfiles
- `tests/` - Unit and integration tests
- `docs/` - Documentation

**And** root includes: `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`
**And** each Python component has `pyproject.toml` with dependencies
**And** shared `common/` package is installable via `pip install -e common/`

## Technical Notes

- Use Poetry or uv for Python dependency management
- Monorepo pattern from architecture.md Decision 1
- Reference: architecture.md lines 17-21

## Definition of Done

- [ ] All directory structure created as specified
- [ ] Root pyproject.toml configured with workspace/monorepo support
- [ ] Each Python component has its own pyproject.toml
- [ ] common/ package is installable and importable
- [ ] .gitignore includes Python, Node.js, and IDE files
- [ ] README.md has basic project overview and setup instructions
- [ ] Tests pass (if any initial tests created)
