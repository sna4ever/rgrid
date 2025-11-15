# Story 1.4: Build CLI Framework with Click

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.4
**Status:** drafted
**Prerequisites:** Story 1.1, Story 1.3

## User Story

As a developer,
I want a CLI framework using Click with proper command structure and error handling,
So that users can execute `rgrid` commands with intuitive interface.

## Acceptance Criteria

**Given** the cli/ package structure
**When** CLI is installed via `pip install -e cli/`
**Then** `rgrid` command is available globally
**And** `rgrid --version` shows current version
**And** `rgrid --help` lists all available commands

**When** user runs `rgrid <command>`
**Then** CLI loads credentials from `~/.rgrid/credentials`
**And** sends authenticated requests to API
**And** displays results in user-friendly format (not raw JSON)
**And** errors show actionable messages (not stack traces)

**And** CLI supports these initial commands:
- `rgrid init` - Initialize credentials
- `rgrid run <script>` - Execute script (stub for now)
- `rgrid status <execution-id>` - Check status (stub for now)
- `rgrid logs <execution-id>` - View logs (stub for now)

## Technical Notes

- Use Click framework for command structure
- CLI structure: cli/rgrid/commands/init.py, run.py, status.py, logs.py
- Credentials path: `~/.rgrid/credentials` (INI format like AWS)
- HTTP client: httpx (async support for future)
- Reference: PRD CLI specification (lines 2255-2390)

## Definition of Done

- [ ] cli/ package created with proper structure
- [ ] Click-based command framework implemented
- [ ] `rgrid` command installable and accessible globally
- [ ] --version flag shows version from pyproject.toml
- [ ] --help flag shows command list with descriptions
- [ ] Credentials loading from ~/.rgrid/credentials implemented
- [ ] httpx client configured for API requests
- [ ] Error handling displays user-friendly messages (no stack traces)
- [ ] Stub commands created: init, run, status, logs
- [ ] Unit tests for CLI framework and credential loading
- [ ] CLI package installable via pip install -e cli/
