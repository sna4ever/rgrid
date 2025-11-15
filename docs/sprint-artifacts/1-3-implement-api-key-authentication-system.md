# Story 1.3: Implement API Key Authentication System

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.3
**Status:** drafted
**Prerequisites:** Story 1.1, Story 1.2

## User Story

As a developer,
I want a secure API key authentication system following AWS credentials pattern,
So that CLI users can authenticate without exposing secrets in project files.

## Acceptance Criteria

**Given** the database schema for `api_keys` table (see architecture.md)
**When** a user generates an API key
**Then** the key is bcrypt-hashed before storage
**And** the key follows format: `sk_live_` + 32 random characters
**And** keys are stored in `api_keys` table with account_id, created_at, last_used_at

**When** CLI sends request with API key in Authorization header
**Then** FastAPI validates key via dependency injection `get_authenticated_account()`
**And** account is loaded from database
**And** `last_used_at` timestamp is updated
**And** invalid keys return 401 Unauthorized with clear error message

**When** API key is revoked
**Then** subsequent requests with that key are rejected
**And** revocation is logged for audit

## Technical Notes

- Use bcrypt for hashing (secure, slow by design)
- FastAPI dependency: `Depends(get_authenticated_account)` on all routes
- Store API keys ONLY in `~/.rgrid/credentials` (never in git)
- Reference: architecture.md Decision 6 (lines 44-48), DB schema for api_keys table
- Implement as pure service function for testability

## Definition of Done

- [ ] `api_keys` table created in database schema
- [ ] API key generation function implemented (sk_live_ prefix + 32 random chars)
- [ ] bcrypt hashing implemented for key storage
- [ ] `get_authenticated_account()` FastAPI dependency implemented
- [ ] API key validation logic implemented
- [ ] last_used_at timestamp update on each request
- [ ] Revocation functionality implemented
- [ ] Unit tests for key generation, validation, and revocation
- [ ] 401 error responses have clear, actionable messages
- [ ] Security: Keys never logged or exposed in responses
