# Epic Technical Specification: Web Interfaces & MVP Polish

Date: 2025-11-15
Author: BMad
Epic ID: 10
Status: Draft

---

## Overview

Epic 10 completes the RGrid MVP by adding web interfaces, production-ready error handling, reliability features, and extensibility foundations. This epic transforms RGrid from a CLI-focused tool to a complete platform with a marketing website for user acquisition, a web console for non-CLI users, robust error handling with actionable messages, network resilience with auto-retry, manual retry capabilities, and custom metadata tagging for workflow integration.

The implementation focuses on making RGrid production-ready and accessible to a broader audience while maintaining the CLI-first philosophy. This epic delivers the final polish needed for public launch - clear error messages, graceful degradation, and web-based access.

## Objectives and Scope

**In Scope:**
- Marketing website landing page (Next.js static site)
- Web console dashboard with execution history (Next.js + Clerk auth)
- Download outputs via web console (presigned URL downloads)
- Structured error handling with user-friendly messages (common error detection)
- Network failure graceful handling (retry with exponential backoff)
- Manual retry command: `rgrid retry <exec_id>`
- Auto-retry for transient failures (worker death, network timeout)
- Execution metadata tagging: `--metadata key=value` flag
- Metadata query: `rgrid list --metadata project=ml-model`

**Out of Scope:**
- Advanced web console features (real-time log viewer, interactive notebooks)
- User management UI (account settings, API key rotation)
- Payment/billing UI (Stripe integration, invoices)
- Mobile app (deferred to post-MVP)
- Admin dashboard (user analytics, system health)

## System Architecture Alignment

**Components Involved:**
- **Website (website/)**: Next.js 14 static marketing site (App Router)
- **Console (console/)**: Next.js 14 dashboard (App Router, Clerk auth)
- **API (api/)**: Endpoints for console, error responses, retry logic
- **CLI (cli/)**: Error handling, retry command, metadata flags
- **Database (Postgres)**: Metadata storage (JSONB column)

**Architecture Constraints:**
- Website deployed to Vercel or control plane (static export)
- Console deployed to Vercel (SSR with API routes)
- Clerk handles authentication (no custom auth in console)
- Error messages follow template pattern (error code → user message)
- Retry logic uses execution cloning (new execution with same params)

**Cross-Epic Dependencies:**
- Requires Epic 1: API infrastructure, authentication
- Requires Epic 8: Status/logs APIs for console display
- Requires Epic 9: Cost display in console
- Leverages all previous epics for complete console functionality

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **Marketing Website** (`website/`) | Landing page, docs, signup CTA | None (static) | HTML pages | Web Team |
| **Console Dashboard** (`console/`) | Execution history, status, logs UI | User session (Clerk) | Interactive dashboard | Web Team |
| **Error Handler** (`api/middleware/errors.py`) | Map exceptions to user-friendly messages | Exception type | Error response | API Team |
| **Retry Service** (`api/services/retry.py`) | Clone execution for retry | Execution ID | New execution ID | API Team |
| **CLI Error Display** (`cli/rgrid/errors.py`) | Format error messages for CLI | Error response | Formatted CLI output | CLI Team |
| **CLI Retry Command** (`cli/rgrid/commands/retry.py`) | Retry failed executions | Execution ID | New execution ID | CLI Team |
| **Metadata Manager** (`api/services/metadata.py`) | Store/query metadata tags | Execution ID, tags | Metadata record | API Team |

### Data Models and Contracts

**Execution Metadata (Updates to `executions` table):**
```python
class Execution(Base):
    # ... existing fields from Epic 2/8/9 ...

    # Epic 10 additions:
    metadata: dict             # JSONB: {project: "ml-model", env: "prod", version: "1.2.3"}
    retry_count: int           # Number of times this execution has been retried
    retry_of: str              # Original execution ID (if this is a retry)
    retried_by: str            # New execution ID (if this was retried)
```

**Error Response (Structured):**
```python
# Standard error response format
class ErrorResponse(BaseModel):
    error_code: str            # Machine-readable code (e.g., "missing_dependency")
    error_message: str         # User-friendly message
    error_details: dict        # Additional context
    suggested_fix: Optional[str]  # Actionable fix suggestion
    docs_url: Optional[str]    # Link to documentation

# Example:
{
  "error_code": "missing_dependency",
  "error_message": "Script failed: Module 'pandas' not found",
  "error_details": {
    "module": "pandas",
    "runtime": "python:3.11"
  },
  "suggested_fix": "Add 'pandas' to requirements.txt or use --runtime python:3.11-datascience",
  "docs_url": "https://docs.rgrid.dev/errors/missing-dependency"
}
```

**Retry Request:**
```python
# POST /api/v1/executions/{exec_id}/retry
class RetryRequest(BaseModel):
    retry_reason: Optional[str]  # User-provided reason (e.g., "network timeout")

# Response:
class RetryResponse(BaseModel):
    original_execution_id: str
    new_execution_id: str      # New execution created for retry
    status: str                # "queued"
```

### APIs and Interfaces

**Error Handling Middleware:**
```python
# api/middleware/errors.py
ERROR_TEMPLATES = {
    "missing_dependency": {
        "message": "Script failed: Module '{module}' not found",
        "fix": "Add '{module}' to requirements.txt or use a runtime with pre-installed packages",
        "docs": "https://docs.rgrid.dev/errors/missing-dependency"
    },
    "script_syntax_error": {
        "message": "Script has syntax errors",
        "fix": "Check script for Python syntax errors before submitting",
        "docs": "https://docs.rgrid.dev/errors/syntax-error"
    },
    "timeout": {
        "message": "Execution exceeded timeout limit",
        "fix": "Optimize script or increase timeout (future feature)",
        "docs": "https://docs.rgrid.dev/errors/timeout"
    },
    "worker_died": {
        "message": "Worker crashed during execution",
        "fix": "Execution will be automatically retried on a different worker",
        "docs": "https://docs.rgrid.dev/errors/worker-failure"
    },
    # ... more templates
}

def handle_execution_error(exception: Exception, execution: Execution) -> ErrorResponse:
    """
    Map exception to user-friendly error response.

    Strategy:
    1. Detect error type (ModuleNotFoundError, SyntaxError, timeout, etc.)
    2. Extract relevant details (module name, line number, etc.)
    3. Look up error template
    4. Populate template with details
    5. Return structured ErrorResponse
    """
    if isinstance(exception, ModuleNotFoundError):
        module = extract_module_name(exception)
        return ErrorResponse(
            error_code="missing_dependency",
            error_message=ERROR_TEMPLATES["missing_dependency"]["message"].format(module=module),
            error_details={"module": module, "runtime": execution.runtime},
            suggested_fix=ERROR_TEMPLATES["missing_dependency"]["fix"].format(module=module),
            docs_url=ERROR_TEMPLATES["missing_dependency"]["docs"]
        )
    elif isinstance(exception, SyntaxError):
        return ErrorResponse(
            error_code="script_syntax_error",
            error_message=ERROR_TEMPLATES["script_syntax_error"]["message"],
            error_details={"line": exception.lineno, "offset": exception.offset},
            suggested_fix=ERROR_TEMPLATES["script_syntax_error"]["fix"],
            docs_url=ERROR_TEMPLATES["script_syntax_error"]["docs"]
        )
    # ... more error types
    else:
        # Generic error (unknown type)
        return ErrorResponse(
            error_code="execution_failed",
            error_message=f"Execution failed: {str(exception)}",
            error_details={},
            suggested_fix="Check logs for details: rgrid logs {exec_id}",
            docs_url="https://docs.rgrid.dev/errors/general"
        )
```

**CLI Error Display:**
```python
# cli/rgrid/errors.py
def display_error(error_response: ErrorResponse):
    """
    Display structured error in CLI with color formatting.

    Example output:
    ❌ Execution failed: exec_abc123

    Error: Script failed: Module 'pandas' not found

    Cause: ModuleNotFoundError in script.py

    Fix: Add 'pandas' to requirements.txt or use --runtime python:3.11-datascience

    Docs: https://docs.rgrid.dev/errors/missing-dependency
    Logs: rgrid logs exec_abc123
    """
    print(f"❌ Execution failed: {error_response.execution_id}\n")
    print(f"Error: {error_response.error_message}\n")

    if error_response.error_details:
        print(f"Cause: {format_error_details(error_response.error_details)}\n")

    if error_response.suggested_fix:
        print(f"Fix: {error_response.suggested_fix}\n")

    if error_response.docs_url:
        print(f"Docs: {error_response.docs_url}")

    print(f"Logs: rgrid logs {error_response.execution_id}")
```

**Retry Service:**
```python
# api/services/retry.py
async def retry_execution(execution_id: str, reason: Optional[str] = None) -> str:
    """
    Clone execution for retry.

    Flow:
    1. Load original execution
    2. Create new execution with same script, args, runtime, env
    3. Link via retry_of / retried_by fields
    4. Increment retry_count
    5. Submit to Ray queue

    Args:
        execution_id: Original execution ID
        reason: Optional user-provided retry reason

    Returns:
        New execution ID

    Raises:
        ValueError: If original execution not found or still running
    """
    # Load original execution
    original = await db.get_execution(execution_id)
    if not original:
        raise ValueError(f"Execution not found: {execution_id}")

    if original.status in ["queued", "running"]:
        raise ValueError(f"Cannot retry running execution: {execution_id}")

    # Create new execution (clone)
    new_execution = await db.create_execution(
        account_id=original.account_id,
        script_content=original.script_content,
        script_filename=original.script_filename,
        runtime=original.runtime,
        args=original.args,
        env_vars=original.env_vars,
        metadata=original.metadata,  # Preserve metadata
        retry_of=execution_id,       # Link to original
        retry_count=original.retry_count + 1
    )

    # Update original execution (link to retry)
    await db.update_execution(execution_id, retried_by=new_execution.execution_id)

    # Submit to Ray queue
    await submit_to_ray(new_execution.execution_id)

    logger.info(f"Retrying {execution_id} as {new_execution.execution_id}, reason: {reason}")

    return new_execution.execution_id
```

**Auto-Retry Logic:**
```python
# runner/executor.py (updated for auto-retry)
TRANSIENT_ERRORS = [
    "worker_died",
    "network_timeout",
    "container_startup_failed"
]

async def execute_with_retry(execution_id: str):
    """
    Execute with automatic retry for transient failures.

    Max retries: 2 (default)
    """
    execution = await db.get_execution(execution_id)
    max_retries = 2

    try:
        result = await execute_script(execution_id)
        return result

    except Exception as e:
        error_code = classify_error(e)

        # Check if transient error and retries remaining
        if error_code in TRANSIENT_ERRORS and execution.retry_count < max_retries:
            logger.info(f"Transient error ({error_code}), auto-retrying {execution_id}")

            # Update execution metadata (track auto-retry)
            await db.update_execution(
                execution_id,
                metadata={
                    **execution.metadata,
                    "auto_retry_reason": error_code,
                    "auto_retry_attempt": execution.retry_count + 1
                }
            )

            # Create retry execution
            new_exec_id = await retry_execution(execution_id, reason=f"Auto-retry: {error_code}")

            # Return retry execution ID (original execution marked as failed, retry is new execution)
            return new_exec_id

        else:
            # Non-transient error or max retries exceeded
            logger.error(f"Execution failed permanently: {execution_id}, error: {error_code}")
            raise
```

**Metadata Tagging:**
```python
# cli/rgrid/commands/run.py (updated)
async def run_command(
    script: Path,
    args: List[str],
    metadata: Dict[str, str] = None,  # --metadata project=ml-model --metadata env=prod
    ...
):
    """
    Run script with custom metadata tags.
    """
    # Parse metadata flags
    # CLI: --metadata project=ml-model --metadata env=prod
    # Parsed: {"project": "ml-model", "env": "prod"}

    execution_id = await api_client.create_execution(
        script_content=script.read_text(),
        metadata=metadata,  # Stored as JSONB in database
        ...
    )

    print(f"Execution started: {execution_id}")
    if metadata:
        print(f"Metadata: {json.dumps(metadata, indent=2)}")
```

**Metadata Query:**
```python
# cli/rgrid/commands/list.py
async def list_command(metadata: Dict[str, str] = None):
    """
    List executions filtered by metadata.

    Example: rgrid list --metadata project=ml-model
    """
    executions = await api_client.list_executions(metadata_filter=metadata)

    print(f"Found {len(executions)} executions:")
    for execution in executions:
        print(f"  {execution.execution_id}: {execution.script_filename} "
              f"({execution.status}, {execution.created_at})")
        if execution.metadata:
            print(f"    Metadata: {json.dumps(execution.metadata)}")
```

**Web Console (Console Dashboard):**
```typescript
// console/app/dashboard/page.tsx
export default function DashboardPage() {
  const { data: executions } = useExecutions(); // Fetch from API

  return (
    <div>
      <h1>Executions</h1>
      <table>
        <thead>
          <tr>
            <th>Execution ID</th>
            <th>Script</th>
            <th>Status</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Cost</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {executions.map(exec => (
            <tr key={exec.execution_id}>
              <td>{exec.execution_id}</td>
              <td>{exec.script_filename}</td>
              <td><StatusBadge status={exec.status} /></td>
              <td>{formatDate(exec.started_at)}</td>
              <td>{formatDuration(exec.duration_seconds)}</td>
              <td>{exec.cost_display}</td>
              <td>
                <button onClick={() => viewLogs(exec.execution_id)}>Logs</button>
                <button onClick={() => downloadOutputs(exec.execution_id)}>Download</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Workflows and Sequencing

**Error Handling Flow:**
```
1. SCRIPT EXECUTION FAILS:
   a. Container exits with code 1
   b. Container stderr: "ModuleNotFoundError: No module named 'pandas'"

2. RUNNER:
   a. Detect failure (exit_code != 0)
   b. Parse stderr for error type
   c. Classify error: "missing_dependency"
   d. Create error metadata:
      {
        "error_code": "missing_dependency",
        "module": "pandas",
        "runtime": "python:3.11"
      }
   e. Update execution: status=failed, exit_code=1, error_metadata=...

3. CLI (user runs: rgrid logs exec_abc123):
   a. API returns execution with error_metadata
   b. CLI formats error:
      ❌ Execution failed: exec_abc123

      Error: Script failed: Module 'pandas' not found

      Cause: ModuleNotFoundError in script.py

      Fix: Add 'pandas' to requirements.txt or use --runtime python:3.11-datascience

      Docs: https://docs.rgrid.dev/errors/missing-dependency
      Logs: rgrid logs exec_abc123

4. USER: Reads fix, updates requirements.txt, retries
```

**Manual Retry Flow:**
```
1. USER: rgrid retry exec_abc123

2. CLI → API: POST /api/v1/executions/exec_abc123/retry

3. API RETRY SERVICE:
   a. Load original execution
   b. Verify not running (status=failed)
   c. Clone execution:
      - Same script, args, runtime, env
      - retry_of=exec_abc123
      - retry_count=1
   d. Create new execution: exec_def456
   e. Link: exec_abc123.retried_by = exec_def456
   f. Submit to Ray queue

4. CLI: Display
   Retrying exec_abc123 as exec_def456
   Track progress: rgrid status exec_def456

5. NEW EXECUTION RUNS:
   a. Worker executes exec_def456
   b. (Hopefully succeeds this time after user fixed issue)
```

**Auto-Retry Flow (Transient Failure):**
```
1. WORKER CRASHES:
   a. Worker dies mid-execution (OOM, hardware failure)
   b. Execution stuck in "running" state

2. ORCHESTRATOR (heartbeat monitor):
   a. Detect dead worker (no heartbeat >120s)
   b. Find running executions on dead worker
   c. Mark executions as failed with error: "worker_died"

3. RUNNER (execute_with_retry logic):
   a. Classify error: "worker_died" (transient)
   b. Check retry_count: 0 (first failure)
   c. Auto-retry enabled: Yes (retry_count < max_retries=2)
   d. Create retry execution automatically
   e. New execution: exec_ghi789 (retry_of=exec_abc123)

4. CLI (user was watching):
   a. Display: "⚠ Worker failure detected. Auto-retrying execution..."
   b. Display: "New execution ID: exec_ghi789"
   c. Continue streaming logs for exec_ghi789

5. RETRY SUCCEEDS:
   a. New worker executes exec_ghi789
   b. Completes successfully
   c. User sees seamless recovery (minimal interruption)

Result: Automatic recovery from transient failures without user intervention
```

**Web Console Workflow:**
```
1. USER: Visits https://app.rgrid.dev

2. CLERK AUTH:
   a. User signs in (or already authenticated)
   b. Clerk issues session token

3. CONSOLE:
   a. Fetch executions: GET /api/v1/executions (with Clerk token)
   b. API validates token, returns user's executions
   c. Display execution history table

4. USER: Clicks "Download" on completed execution

5. CONSOLE:
   a. Fetch presigned URLs: GET /api/v1/executions/{exec_id}/outputs
   b. API generates presigned GET URLs (1-hour expiry)
   c. Console creates download links
   d. User clicks link → browser downloads from MinIO directly

6. USER: Clicks "Logs" on execution

7. CONSOLE:
   a. Fetch logs: GET /api/v1/executions/{exec_id}/logs
   b. Display logs in modal or separate page
   c. Syntax highlighting for stdout/stderr
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Website load time**: < 1 second (static, pre-rendered)
- **Console initial load**: < 2 seconds (SSR + data fetch)
- **Console execution list**: < 500ms (paginated, 50 per page)
- **Error classification**: < 10ms (regex matching)
- **Retry execution creation**: < 200ms (database clone + queue submit)

**Scalability:**
- Console supports 10,000 executions per user (paginated)
- Error templates: 50 common error types

**Source:** Architecture performance targets

### Security

**Web Console:**
- Clerk authentication (OAuth 2.0, secure by default)
- All API calls require valid session token
- No API keys exposed in frontend

**Error Messages:**
- No sensitive data in error messages (API keys, credentials)
- Stack traces only in logs, not in user-facing errors

**Source:** Architecture security decisions

### Reliability/Availability

**Error Handling:**
- All errors mapped to user-friendly messages (no raw exceptions)
- Unknown errors default to generic message + logs link

**Auto-Retry:**
- Transient failures automatically retried (max 2 retries)
- Non-transient failures not retried (avoid infinite loops)

**Network Resilience:**
- CLI retries HTTP requests with exponential backoff (max 5 retries)
- Graceful degradation on API unavailability

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Error rate by error_code
- Retry rate (manual vs. auto)
- Console page views, user sessions
- Website conversion rate (visits → signups)

**Logging:**
- API: Error classification events, retry events
- Console: User interactions, API errors

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Frontend Framework:**
```json
// website/package.json & console/package.json
{
  "dependencies": {
    "next": "14.0.0",
    "react": "18.2.0",
    "@clerk/nextjs": "^4.27.0",
    "tailwindcss": "^3.3.0"
  }
}
```

**Database Schema Updates:**
```sql
-- Updates to executions table
ALTER TABLE executions ADD COLUMN metadata JSONB DEFAULT '{}';
ALTER TABLE executions ADD COLUMN retry_count INT DEFAULT 0;
ALTER TABLE executions ADD COLUMN retry_of VARCHAR(64);
ALTER TABLE executions ADD COLUMN retried_by VARCHAR(64);
ALTER TABLE executions ADD COLUMN error_metadata JSONB;

-- Index for metadata queries
CREATE INDEX idx_executions_metadata ON executions USING gin(metadata);

-- Index for retry chains
CREATE INDEX idx_executions_retry_of ON executions(retry_of);
```

**Deployment:**
- **Website**: Vercel (static export, CDN)
- **Console**: Vercel (SSR, serverless functions)
- **Clerk**: SaaS (authentication provider)

## Acceptance Criteria (Authoritative)

**AC-10.1: Marketing Website Landing Page**
1. Website accessible at https://rgrid.dev
2. Hero section shows value proposition: "Run Python scripts remotely. No infrastructure."
3. Clear CTA button: "Get Started" → https://app.rgrid.dev/signup
4. Features section highlights simplicity, cost, scale

**AC-10.2: Console Dashboard with Execution History**
1. User logs in via Clerk at https://app.rgrid.dev
2. Dashboard displays table of executions (ID, script, status, started, duration, cost)
3. Click execution → detail view with metadata, logs link

**AC-10.3: Download Outputs via Console**
1. Execution detail page lists output files
2. User clicks "Download" → file downloads via presigned URL

**AC-10.4: Structured Error Handling**
1. When execution fails, error_metadata stored with error_code, message, suggested_fix
2. CLI displays actionable error message (not stack trace)

**AC-10.5: Network Failure Graceful Handling**
1. When CLI HTTP request fails, CLI retries with exponential backoff (max 5 retries)
2. CLI displays: "Connection lost. Retrying... (attempt 2/5)"
3. On persistent failure: "Network error. Check connection and retry."

**AC-10.6: Manual Retry Command**
1. When I run `rgrid retry <exec_id>`, API creates new execution with same params
2. New execution linked via retry_of field
3. CLI displays: "Retrying {orig_id} as {new_id}"

**AC-10.7: Auto-Retry for Transient Failures**
1. When execution fails with transient error (worker_died, network_timeout), runner auto-retries
2. Max 2 retries
3. CLI displays: "Auto-retry 1/2 after worker failure"

**AC-10.8: Execution Metadata Tagging**
1. When I run `rgrid run script.py --metadata project=ml --metadata env=prod`, metadata stored as JSONB
2. I can query: `rgrid list --metadata project=ml` → returns filtered executions

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-10.1 | Marketing Website | website/ | Visit URL, verify page loads, check content |
| AC-10.2 | Console Dashboard | console/ | Login, verify execution table displays |
| AC-10.3 | Console: Downloads | console/ | Click download, verify file downloads |
| AC-10.4 | Error Handler | api/middleware/errors.py | Fail execution, verify error_metadata stored, check CLI display |
| AC-10.5 | CLI: Network Retry | cli/http_client.py | Simulate network failure, verify retries |
| AC-10.6 | Retry Service | api/services/retry.py | Call retry API, verify new execution created |
| AC-10.7 | Auto-Retry | runner/executor.py | Simulate worker failure, verify auto-retry |
| AC-10.8 | Metadata Manager | api/services/metadata.py | Run with --metadata, query, verify filtering |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Auto-retry could mask real issues (infinite retry loops)
   - **Mitigation**: Max 2 retries, only for transient errors
2. **R2**: Error classification may miss edge cases (unknown errors)
   - **Mitigation**: Default to generic error message + logs link

**Assumptions:**
1. **A1**: Clerk handles auth securely (trusted SaaS provider)
2. **A2**: Most errors fall into ~50 common patterns (error templates)
3. **A3**: Users prefer web console for occasional use, CLI for automation

**Open Questions:**
1. **Q1**: Should we implement role-based access control (teams, shared projects)?
   - **Decision**: Deferred to post-MVP (single-user accounts only)
2. **Q2**: Should error messages be customizable per-user?
   - **Decision**: No, standard messages for consistency

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Error classification: Test regex patterns, verify correct error_code
   - Retry logic: Test execution cloning, verify retry_of/retried_by links
   - Metadata parsing: Test --metadata flag parsing

2. **Integration Tests**
   - Website: Load page, verify content
   - Console: Mock Clerk auth, verify execution list displays
   - Error handling: Fail execution, verify error_metadata stored

3. **End-to-End Tests**
   - Complete flow: Run execution → fail with known error → verify CLI displays fix
   - Retry: Fail execution → retry → verify new execution succeeds
   - Auto-retry: Simulate worker failure → verify auto-retry → verify success

**Frameworks:**
- **Frontend**: Jest + React Testing Library
- **E2E**: Playwright for console tests

**Coverage of ACs:**
- AC-10.1: Integration test (load website, check content)
- AC-10.2: Integration test (mock auth, verify dashboard)
- AC-10.3: E2E test (download file via console)
- AC-10.4: E2E test (fail execution, check error message)
- AC-10.5: Unit test (mock network failure, verify retries)
- AC-10.6: Integration test (call retry API, verify clone)
- AC-10.7: E2E test (kill worker, verify auto-retry)
- AC-10.8: Integration test (run with --metadata, query, verify filter)

**Edge Cases:**
- Unknown error type (no template match)
- Retry of already-retried execution (prevent retry chains >2)
- Metadata with special characters (JSON encoding)
- Network failure during retry request (retry the retry)
- Auto-retry max exceeded (mark as permanently failed)

**Performance Tests:**
- Console load time: 1000 executions in table (pagination)
- Error classification: 1000 errors/second (regex throughput)

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 10.1

**🎉 ALL 10 EPICS TECH-SPEC COMPLETE! 🎉**
