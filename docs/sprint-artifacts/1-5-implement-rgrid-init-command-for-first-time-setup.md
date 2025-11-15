# Story 1.5: Implement `rgrid init` Command for First-Time Setup

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.5
**Status:** drafted
**Prerequisites:** Story 1.3, Story 1.4

## User Story

As a developer,
I want `rgrid init` to handle first-time authentication setup,
So that users can authenticate in < 1 minute as per FR2.

## Acceptance Criteria

**Given** a user runs `rgrid init` for the first time
**When** the command executes
**Then** CLI prompts: "Enter your API key (from app.rgrid.dev):"
**And** user enters key (e.g., `sk_live_abc123...`)
**And** CLI validates key by calling `POST /api/v1/auth/validate`
**And** on success, writes to `~/.rgrid/credentials`:
```
[default]
api_key = sk_live_abc123...
```

**And** CLI displays: "✅ Authentication successful! You're ready to run scripts."
**And** execution time < 30 seconds

**When** validation fails (invalid key)
**Then** CLI displays: "❌ Invalid API key. Get your key from: https://app.rgrid.dev/settings/api-keys"
**And** credentials file is NOT created
**And** exit code = 1

**When** user runs `rgrid init` again (credentials exist)
**Then** CLI prompts: "Credentials already exist. Overwrite? (y/n)"
**And** on "y", replaces existing credentials
**And** on "n", exits without changes

## Technical Notes

- Credentials file permissions: chmod 600 (owner read/write only)
- API endpoint: POST /api/v1/auth/validate (returns account info)
- Use `getpass` module for secure password input (no echo)
- Reference: architecture.md Decision 6, PRD authentication section

## Definition of Done

- [ ] `rgrid init` command fully implemented
- [ ] API key prompt implemented with secure input (no echo)
- [ ] POST /api/v1/auth/validate endpoint implemented in API
- [ ] Credentials written to ~/.rgrid/credentials with chmod 600
- [ ] INI format credentials file (AWS-style)
- [ ] Success message displayed on valid key
- [ ] Error message with help URL on invalid key
- [ ] Overwrite protection implemented (prompt on existing credentials)
- [ ] Exit codes: 0 for success, 1 for failure
- [ ] Execution completes in < 30 seconds
- [ ] Unit tests for init command logic
- [ ] Integration test with mock API
