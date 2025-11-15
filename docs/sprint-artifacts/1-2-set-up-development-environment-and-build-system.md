# Story 1.2: Set Up Development Environment and Build System

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.2
**Status:** drafted
**Prerequisites:** Story 1.1

## User Story

As a developer,
I want a consistent development environment with automated build and test commands,
So that I can quickly iterate on code changes across all components.

## Acceptance Criteria

**Given** the monorepo structure from Story 1.1
**When** I run `make setup`
**Then** all Python dependencies are installed
**And** pre-commit hooks are configured (black, ruff, mypy)
**And** development database is initialized (PostgreSQL via Docker Compose)
**And** MinIO storage is running locally (Docker Compose)

**When** I run `make test`
**Then** all unit tests execute across api/, orchestrator/, runner/, cli/
**And** test coverage report is generated
**And** minimum 80% coverage is enforced

**When** I run `make lint`
**Then** code is formatted with black
**And** linting passes with ruff
**And** type checking passes with mypy

## Technical Notes

- Use Docker Compose for local PostgreSQL + MinIO
- Makefile targets: setup, test, lint, format, clean
- Pre-commit hooks prevent commits that fail linting
- Reference: Architecture LLM-friendly patterns (architecture.md lines 179-190)

## Definition of Done

- [ ] Makefile created with all required targets (setup, test, lint, format, clean)
- [ ] Docker Compose file created with PostgreSQL and MinIO services
- [ ] Pre-commit hooks configured and working
- [ ] `make setup` successfully installs all dependencies
- [ ] `make test` runs and reports coverage (80% minimum enforced)
- [ ] `make lint` checks formatting, linting, and type checking
- [ ] All Python components have test directories with pytest configured
- [ ] Development environment documentation added to README.md
