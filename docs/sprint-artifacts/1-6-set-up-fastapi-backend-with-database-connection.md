# Story 1.6: Set Up FastAPI Backend with Database Connection

**Epic:** Epic 1 - Foundation & CLI Core
**Story ID:** 1.6
**Status:** drafted
**Prerequisites:** Story 1.1, Story 1.2, Story 1.3

## User Story

As a developer,
I want a FastAPI application with PostgreSQL connection and basic health check,
So that API can serve authenticated requests from CLI.

## Acceptance Criteria

**Given** the api/ package structure
**When** FastAPI app starts
**Then** database connection pool is initialized (asyncpg)
**And** MinIO client is initialized (boto3)
**And** app serves on http://localhost:8000

**When** GET /health is called
**Then** response is 200 OK with:
```json
{
  "status": "healthy",
  "database": "connected",
  "storage": "connected",
  "version": "0.1.0"
}
```

**When** POST /api/v1/auth/validate is called with valid API key
**Then** response is 200 OK with account info:
```json
{
  "account_id": "acct_abc123",
  "email": "user@example.com",
  "credits_balance_micros": 1000000
}
```

**When** called with invalid API key
**Then** response is 401 Unauthorized

## Technical Notes

- FastAPI + Uvicorn for async server
- SQLAlchemy 2.0 + asyncpg for database ORM
- Database URL from environment: `DATABASE_URL=postgresql+asyncpg://...`
- MinIO credentials from environment
- Reference: architecture.md Decision 7 (API structure), DB schema
- Use Pydantic models for all requests/responses

## Definition of Done

- [ ] FastAPI application initialized in api/ package
- [ ] SQLAlchemy 2.0 models created for accounts, api_keys tables
- [ ] Database connection pool configured (asyncpg)
- [ ] MinIO client initialized
- [ ] GET /health endpoint implemented with all checks
- [ ] POST /api/v1/auth/validate endpoint implemented
- [ ] Pydantic schemas created for all request/response models
- [ ] Environment variables loaded via python-dotenv
- [ ] Uvicorn server starts successfully
- [ ] Database migrations set up (Alembic)
- [ ] Unit tests for health and auth endpoints
- [ ] API documentation auto-generated (FastAPI /docs)
- [ ] Proper error responses with ErrorResponse Pydantic model
