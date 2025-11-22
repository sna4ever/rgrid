# Story 9.5: Implement Cost Alerts (Future Enhancement)

Status: done

## Story

As developer,
I want to set spending limits and receive alerts,
So that I can prevent unexpected bills.

## Acceptance Criteria

1. Given** I set spending limit: `rgrid cost set-limit €50/month` ✅
2. When** account approaches 80% of limit ✅ (warning shown in CLI output)
3. Then** API sends email alert ⚠️ (logging alert instead - no SMTP infrastructure)
4. And** at 100%, API blocks new executions ✅ (returns HTTP 402)

## Tasks / Subtasks

- [x] Task 1: CLI set-limit command (AC: #1)
  - [x] Parse limit values (€50, EUR50, 50, €50/month)
  - [x] API client method for setting limits
  - [x] CLI subcommand `rgrid cost set-limit <amount>`
- [x] Task 2: 80% warning threshold (AC: #2)
  - [x] Calculate usage percentage
  - [x] Display warning in `rgrid cost` output
  - [x] Display warning in `rgrid cost show-limit`
- [x] Task 3: Alert logging (AC: #3)
  - [x] Track last alert timestamps per API key
  - [x] Log alerts instead of email (no SMTP infrastructure)
  - [x] Alert once per month per threshold
- [x] Task 4: Block at 100% (AC: #4)
  - [x] Check limit in POST /executions
  - [x] Return HTTP 402 Payment Required with clear message
  - [x] Also check in retry endpoint

## Dev Notes

### Prerequisites

Story 9.3 ✅ (rgrid cost command exists)

### Technical Notes

**Implementation approach:**
- Spending limits stored in new `spending_limits` table
- Limits tied to API key hash for per-key limits
- MICRONS pattern used (same as cost tracking)
- 80% warning: shown in CLI output (not email - no SMTP infrastructure)
- 100% blocking: HTTP 402 returned on execution creation

**Note on AC #3 (email alerts):**
The codebase has no existing email/SMTP infrastructure. Rather than add external dependencies
for a single feature, this implementation:
- Logs the alert to server logs
- Shows warning in CLI `rgrid cost` and `rgrid cost show-limit`
- Returns warning status in GET /cost/limit API response

Email alerts can be added as a future enhancement when email infrastructure is established.

### References

- [Source: docs/epics.md - Story 9.5]
- [Source: docs/sprint-artifacts/tech-spec-epic-9.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/9-5-implement-cost-alerts-future-enhancement.context.xml

### Agent Model Used

claude-sonnet-4-5-20250929 (Dev 2)

### Debug Log References

N/A - clean implementation

### Completion Notes List

1. Created SpendingLimit database model with migration
2. Added API endpoints: GET/PUT/DELETE /api/v1/cost/limit
3. Updated CLI to command group with set-limit, show-limit, remove-limit subcommands
4. Added spending limit check to POST /executions (returns 402 when exceeded)
5. Added 33 unit tests for spending limits feature
6. All 851 tests pass

### File List

- `cli/rgrid/spending_limits.py` - Helper functions (parsing, status calculation)
- `cli/rgrid/commands/cost.py` - CLI cost command with subcommands
- `cli/rgrid/api_client.py` - API client methods for spending limits
- `api/app/models/spending_limit.py` - SpendingLimit database model
- `api/app/models/__init__.py` - Added SpendingLimit export
- `api/app/api/v1/cost.py` - API endpoints for spending limits
- `api/app/api/v1/executions.py` - Added limit check in create_execution
- `api/alembic/versions/e5f6a7b8c9d0_add_spending_limits_table_story_9_5.py` - Migration
- `tests/unit/test_cost_alerts.py` - 33 unit tests for spending limits
