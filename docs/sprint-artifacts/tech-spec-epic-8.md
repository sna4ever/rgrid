# Epic Technical Specification: Observability & Real-time Feedback

Date: 2025-11-15
Author: BMad
Epic ID: 8
Status: Draft

---

## Overview

Epic 8 transforms RGrid from a "black box" execution system to a fully transparent, observable platform with comprehensive visibility into execution state, real-time log streaming, and rich metadata tracking. By implementing `rgrid status` and `rgrid logs` commands, WebSocket-based log streaming, CLI reconnection capabilities, batch progress displays, and execution metadata collection, this epic ensures developers always know exactly what's happening with their jobs.

The implementation focuses on developer experience - providing instant status updates, streaming logs with <1 second latency, automatic reconnection resilience, and aggregate progress tracking for batch operations. This epic delivers on the "no black box" promise, making remote execution feel as transparent as local execution.

## Objectives and Scope

**In Scope:**
- `rgrid status <exec_id>` command (execution status, duration, worker, cost)
- `rgrid logs <exec_id>` command (historical logs from database)
- WebSocket log streaming with `rgrid logs <exec_id> --follow` (real-time, <1s latency)
- CLI reconnection logic (auto-resume log streaming after network blips)
- Batch progress display with `--watch` flag (aggregate progress, ETA, drill-down)
- Execution metadata tracking (start/end times, exit code, worker, cost, logs)
- `execution_logs` table (structured log storage)
- Cursor-based log resumption (no duplicates, no skipped lines)

**Out of Scope:**
- Distributed tracing (OpenTelemetry deferred to post-MVP)
- Metrics dashboard (Grafana/Prometheus integration post-MVP)
- Alerting system (Slack/email notifications post-MVP)
- Log aggregation across executions (search all logs)
- Log retention policy >30 days (same as artifacts)

## System Architecture Alignment

**Components Involved:**
- **CLI (cli/)**: Status/logs commands, WebSocket client, progress display
- **API (api/)**: Status endpoints, historical logs, WebSocket server
- **Runner (runner/)**: Log capture, WebSocket streaming to API
- **Database (Postgres)**: execution_logs table (structured logs with sequence numbers)

**Architecture Constraints:**
- WebSocket protocol for real-time log streaming (HTTP upgrade)
- Runner streams logs to API via WebSocket (API broadcasts to CLI)
- Logs stored with sequence numbers (cursor-based resumption)
- CLI reconnection uses last_sequence_number to resume
- Progress polling every 2 seconds (until WebSocket replaces for batch)

**Cross-Epic Dependencies:**
- Requires Epic 1: API infrastructure, CLI framework
- Requires Epic 2: Execution basics, exit codes
- Requires Epic 5: Batch execution for progress tracking
- Feeds Epic 9: Cost data displayed in status command
- Feeds Epic 10: Web console uses same status/logs APIs

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **CLI Status Command** (`cli/rgrid/commands/status.py`) | Query and display execution status | Execution ID | Formatted status display | CLI Team |
| **CLI Logs Command** (`cli/rgrid/commands/logs.py`) | Fetch and stream logs | Execution ID, --follow flag | Logs (historical or real-time) | CLI Team |
| **API Status Service** (`api/services/status.py`) | Aggregate execution metadata | Execution ID | ExecutionStatus response | API Team |
| **API Logs Service** (`api/services/logs.py`) | Retrieve historical logs from DB | Execution ID, cursor | Log entries | API Team |
| **WebSocket Server** (`api/websocket/logs.py`) | Stream logs to CLI clients | Execution ID | Real-time log events | API Team |
| **Runner Log Streamer** (`runner/log_streamer.py`) | Capture container logs, stream to API | Container stdout/stderr | Log lines with sequence numbers | Runner Team |
| **CLI Progress Tracker** (`cli/rgrid/batch/progress.py`) | Display batch progress with --watch | Batch ID | Progress bar, ETA, stats | CLI Team |
| **Execution Metadata Tracker** (`api/services/metadata.py`) | Record execution lifecycle events | Execution events | Updated execution record | API Team |

### Data Models and Contracts

**Execution Logs (Postgres `execution_logs` table):**
```python
class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    log_id: str                # Primary key, format: log_{uuid}
    execution_id: str          # Foreign key to executions
    sequence_number: int       # Monotonic counter (0, 1, 2, ...) for ordering
    timestamp: datetime        # Log line timestamp
    stream: str                # "stdout" | "stderr"
    message: str               # Log line content (text)

    # Index for efficient cursor-based queries
    # PRIMARY KEY (execution_id, sequence_number)
```

**Execution Record Extended (Updates to `executions` table):**
```python
class Execution(Base):
    # ... existing fields from Epic 2 ...

    # Epic 8 additions:
    started_at: datetime       # When execution actually started (vs. created_at = queued)
    completed_at: datetime     # When execution finished
    duration_seconds: int      # completed_at - started_at
    exit_code: int             # Container exit code (0 = success)

    # Metadata
    worker_hostname: str       # Worker node hostname (e.g., "worker-hetzner-01")
    execution_metadata: dict   # JSONB: {runtime_version, python_version, env_vars_count, ...}

    # Cost (Epic 9, displayed in status)
    cost_micros: int           # Execution cost in microns
```

**Status Response:**
```python
# GET /api/v1/executions/{exec_id}/status
class ExecutionStatusResponse(BaseModel):
    execution_id: str
    status: str                # queued|running|completed|failed
    script_filename: str       # e.g., "process.py"
    runtime: str               # e.g., "python:3.11"

    created_at: datetime       # Queued timestamp
    started_at: Optional[datetime]  # Execution start (null if queued)
    completed_at: Optional[datetime]  # Completion (null if running)
    duration_seconds: Optional[int]   # Runtime duration

    worker_id: Optional[str]   # Worker that executed (null if queued)
    worker_hostname: Optional[str]
    exit_code: Optional[int]   # Container exit code (null if running)

    cost_micros: int           # Execution cost (Epic 9)
    cost_display: str          # "€0.02" (formatted for display)

    artifacts_count: int       # Number of outputs
```

**Logs Response (Historical):**
```python
# GET /api/v1/executions/{exec_id}/logs?cursor=100&limit=50
class LogsResponse(BaseModel):
    execution_id: str
    logs: List[LogEntry]
    next_cursor: Optional[int]  # Sequence number for pagination (null if end)
    has_more: bool

class LogEntry(BaseModel):
    sequence_number: int
    timestamp: datetime
    stream: str                # "stdout" | "stderr"
    message: str               # Log line content
```

**WebSocket Log Message:**
```python
# WebSocket message format (JSON)
{
  "type": "log",
  "execution_id": "exec_abc123",
  "sequence_number": 42,
  "timestamp": "2025-11-15T10:30:15.123Z",
  "stream": "stdout",
  "message": "Processing file data.csv..."
}

# Completion message
{
  "type": "complete",
  "execution_id": "exec_abc123",
  "exit_code": 0,
  "status": "completed"
}

# Error message
{
  "type": "error",
  "execution_id": "exec_abc123",
  "error": "Connection lost to runner"
}
```

### APIs and Interfaces

**CLI Status Command:**
```python
# cli/rgrid/commands/status.py
async def status_command(execution_id: str):
    """
    Display execution status.

    Example output:
    Execution: exec_abc123
    Status: running
    Script: process.py
    Runtime: python:3.11

    Started: 2025-11-15 10:30:15
    Duration: 45s
    Worker: worker-hetzner-01
    Cost: €0.02 (estimated)

    Artifacts: 0 outputs (execution still running)
    """
    response = await api_client.get_status(execution_id)

    # Format and display
    print(f"Execution: {response.execution_id}")
    print(f"Status: {colorize_status(response.status)}")
    print(f"Script: {response.script_filename}")
    print(f"Runtime: {response.runtime}")
    print()

    if response.started_at:
        print(f"Started: {format_datetime(response.started_at)}")
        if response.duration_seconds:
            print(f"Duration: {format_duration(response.duration_seconds)}")
        else:
            elapsed = datetime.utcnow() - response.started_at
            print(f"Duration: {format_duration(elapsed.total_seconds())} (running)")

    if response.worker_hostname:
        print(f"Worker: {response.worker_hostname}")

    print(f"Cost: {response.cost_display}")
    print()
    print(f"Artifacts: {response.artifacts_count} outputs")

    if response.status == "failed":
        print(f"\nExit code: {response.exit_code}")
        print(f"View logs: rgrid logs {execution_id}")
```

**CLI Logs Command (Historical):**
```python
# cli/rgrid/commands/logs.py
async def logs_command(execution_id: str, follow: bool = False):
    """
    Display execution logs (historical or real-time).
    """
    if follow:
        # Real-time streaming via WebSocket
        await stream_logs_websocket(execution_id)
    else:
        # Historical logs from database
        await fetch_historical_logs(execution_id)

async def fetch_historical_logs(execution_id: str):
    """
    Fetch all logs from database (paginated).
    """
    cursor = 0  # Start from beginning
    while True:
        response = await api_client.get_logs(execution_id, cursor=cursor, limit=100)

        for log in response.logs:
            # Format: [timestamp] [stream] message
            timestamp = format_timestamp(log.timestamp)
            stream_color = "blue" if log.stream == "stdout" else "red"
            print(f"[{timestamp}] [{colorize(log.stream, stream_color)}] {log.message}")

        if not response.has_more:
            break

        cursor = response.next_cursor  # Pagination
```

**WebSocket Log Streaming (CLI):**
```python
# cli/rgrid/commands/logs.py
async def stream_logs_websocket(execution_id: str):
    """
    Stream logs in real-time via WebSocket.

    Features:
    - Automatic reconnection on network blip
    - Cursor-based resumption (no duplicates)
    - Display logs as they arrive (<1 second latency)
    """
    last_sequence = -1  # Start from beginning

    while True:
        try:
            async with websockets.connect(
                f"wss://{API_HOST}/ws/executions/{execution_id}/logs?cursor={last_sequence}"
            ) as websocket:
                print(f"Connected to log stream for {execution_id}")

                async for message in websocket:
                    data = json.loads(message)

                    if data["type"] == "log":
                        # Display log line
                        timestamp = format_timestamp(data["timestamp"])
                        stream = data["stream"]
                        msg = data["message"]
                        print(f"[{timestamp}] [{stream}] {msg}")

                        # Update cursor for resumption
                        last_sequence = data["sequence_number"]

                    elif data["type"] == "complete":
                        print(f"\n✓ Execution completed (exit code: {data['exit_code']})")
                        break

                    elif data["type"] == "error":
                        print(f"\n✗ Error: {data['error']}")
                        break

        except websockets.ConnectionClosed:
            print("Connection lost. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            # Reconnect with last_sequence cursor (resume from where we left off)

        except KeyboardInterrupt:
            print("\nDisconnected from log stream")
            break
```

**WebSocket Server (API):**
```python
# api/websocket/logs.py
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/executions/{execution_id}/logs")
async def websocket_logs_endpoint(websocket: WebSocket, execution_id: str, cursor: int = -1):
    """
    WebSocket endpoint for real-time log streaming.

    Args:
        execution_id: Execution ID
        cursor: Last sequence number received by client (for resumption)

    Flow:
    1. Client connects with cursor (last seen sequence)
    2. Send historical logs from cursor+1 to current (catch up)
    3. Subscribe to real-time log stream from runner
    4. Forward logs to client as they arrive
    5. On completion, send "complete" message
    """
    await websocket.accept()

    try:
        # 1. Send historical logs (from cursor+1 to current)
        historical_logs = await db.query(
            """
            SELECT * FROM execution_logs
            WHERE execution_id = :exec_id AND sequence_number > :cursor
            ORDER BY sequence_number ASC
            """,
            {"exec_id": execution_id, "cursor": cursor}
        )

        for log in historical_logs:
            await websocket.send_json({
                "type": "log",
                "execution_id": execution_id,
                "sequence_number": log.sequence_number,
                "timestamp": log.timestamp.isoformat(),
                "stream": log.stream,
                "message": log.message
            })

        # 2. Subscribe to real-time log stream (from runner)
        # Use Redis pub/sub or in-memory event bus
        subscription = await log_bus.subscribe(f"logs:{execution_id}")

        async for log_event in subscription:
            await websocket.send_json({
                "type": "log",
                "execution_id": execution_id,
                "sequence_number": log_event.sequence_number,
                "timestamp": log_event.timestamp.isoformat(),
                "stream": log_event.stream,
                "message": log_event.message
            })

            # Check if execution complete
            if log_event.is_final:
                await websocket.send_json({
                    "type": "complete",
                    "execution_id": execution_id,
                    "exit_code": log_event.exit_code,
                    "status": "completed"
                })
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from logs stream: {execution_id}")
```

**Runner Log Streamer:**
```python
# runner/log_streamer.py
async def stream_container_logs(execution_id: str, container: docker.Container):
    """
    Capture container logs and stream to API via WebSocket.

    Flow:
    1. Connect to container stdout/stderr streams
    2. For each log line:
       a. Assign sequence number (monotonic counter)
       b. Store in database (execution_logs table)
       c. Publish to log_bus (for WebSocket subscribers)
    """
    sequence_number = 0

    # Connect to API log streaming endpoint
    async with websockets.connect(
        f"wss://{API_HOST}/ws/runner/executions/{execution_id}/stream"
    ) as websocket:

        # Stream container logs (stdout and stderr combined)
        for log_line in container.logs(stream=True, stdout=True, stderr=True):
            # Parse log line (Docker prefixes with stream identifier)
            stream, message = parse_docker_log(log_line)

            # Send to API
            await websocket.send_json({
                "execution_id": execution_id,
                "sequence_number": sequence_number,
                "timestamp": datetime.utcnow().isoformat(),
                "stream": stream,
                "message": message
            })

            sequence_number += 1

        # Send completion event
        exit_code = container.wait()["StatusCode"]
        await websocket.send_json({
            "type": "complete",
            "execution_id": execution_id,
            "exit_code": exit_code
        })
```

### Workflows and Sequencing

**Status Command Flow:**
```
1. USER: rgrid status exec_abc123

2. CLI → API: GET /api/v1/executions/exec_abc123/status

3. API:
   a. Query executions table: SELECT * WHERE execution_id='exec_abc123'
   b. Query artifacts table: COUNT(*) WHERE execution_id='exec_abc123' AND artifact_type='output'
   c. Query workers table (if worker_id set): SELECT hostname WHERE worker_id='worker_xyz'
   d. Calculate cost_display: cost_micros / 1,000,000 → "€0.02"

4. API → CLI: ExecutionStatusResponse

5. CLI: Format and display status
   Execution: exec_abc123
   Status: completed ✓
   Script: process.py
   Runtime: python:3.11
   Started: 2025-11-15 10:30:15
   Duration: 1m 23s
   Worker: worker-hetzner-01
   Cost: €0.02
   Artifacts: 2 outputs
```

**Real-Time Log Streaming Flow:**
```
1. USER: rgrid logs exec_abc123 --follow

2. CLI → API: WebSocket connect to /ws/executions/exec_abc123/logs?cursor=-1

3. API:
   a. Accept WebSocket connection
   b. Query historical logs: SELECT * WHERE execution_id='exec_abc123' AND sequence_number > -1
   c. Send historical logs to CLI (catch-up if execution already started)
   d. Subscribe to log_bus (Redis pub/sub) for real-time updates

4. RUNNER (parallel):
   a. Container running: python /work/script.py
   b. Container prints to stdout: "Processing file data.csv..."
   c. Runner captures log line
   d. Runner assigns sequence_number=42
   e. Runner → Database: INSERT INTO execution_logs (exec_id, seq=42, stream='stdout', msg='...')
   f. Runner → log_bus: PUBLISH logs:exec_abc123 {seq=42, stream='stdout', msg='...'}

5. API (log_bus subscriber):
   a. Receive log event from log_bus
   b. Forward to WebSocket: {"type": "log", "sequence_number": 42, "message": "..."}

6. CLI:
   a. Receive WebSocket message
   b. Display: [10:30:15] [stdout] Processing file data.csv...
   c. Update last_sequence=42 (for reconnection)

7. CONTAINER: Exits with code 0

8. RUNNER:
   a. Detect container exit
   b. Send completion event: {"type": "complete", "exit_code": 0}

9. CLI:
   a. Receive completion event
   b. Display: "✓ Execution completed (exit code: 0)"
   c. Close WebSocket connection

Total latency: <1 second from container output to CLI display
```

**CLI Reconnection Flow (Network Blip):**
```
1. CLI: Streaming logs, last_sequence=42

2. NETWORK: Connection drops (temporary network blip)

3. CLI:
   a. Detect websockets.ConnectionClosed exception
   b. Display: "Connection lost. Reconnecting in 5 seconds..."
   c. Wait 5 seconds

4. CLI: Reconnect with cursor=42
   a. WebSocket connect to /ws/executions/exec_abc123/logs?cursor=42

5. API:
   a. Query historical logs: sequence_number > 42
   b. Send logs 43, 44, 45, ... (catch-up)
   c. Subscribe to real-time stream

6. CLI:
   a. Receive catch-up logs (no duplicates, no gaps)
   b. Resume real-time streaming

Result: Seamless reconnection, no log lines missed
```

**Batch Progress Display:**
```
1. USER: rgrid run script.py --batch data/*.csv --watch

2. CLI: Submit batch (Epic 5), batch_id=batch_abc123

3. CLI: Enter progress tracking loop
   while batch not complete:
     a. Poll API: GET /api/v1/batches/batch_abc123/status (every 2 seconds)
     b. Display progress bar:
        [=========>           ] 45/100 complete (3 failed, 10 running, 42 queued)
        Duration: 2m 30s | ETA: 3m 15s | Cost: €0.90
     c. Calculate ETA: (remaining * avg_duration)
     d. Sleep 2 seconds

4. BATCH COMPLETE:
   a. API returns: status='completed', completed_count=97, failed_count=3
   b. CLI displays final summary:
      ✓ Batch complete: 97 succeeded, 3 failed
      Total duration: 5m 42s
      Total cost: €1.82

   c. CLI exits progress loop
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Status query latency**: < 100ms (single database query)
- **Historical logs query**: < 200ms for 10,000 log lines (indexed query)
- **WebSocket log latency**: < 1 second from container output to CLI display
  - Container → Runner: instant (stream)
  - Runner → API: ~50ms (WebSocket send)
  - API → CLI: ~50ms (WebSocket forward)
  - Total: ~100ms + network RTT
- **Progress polling overhead**: < 100ms per poll (batch status aggregation)

**Scalability:**
- Support 1,000 concurrent WebSocket connections (API server)
- Log storage: 100,000 log lines per execution (typical long-running job)
- Database: <1s query for 1M log lines (indexed by execution_id + sequence_number)

**Source:** Architecture performance targets

### Security

**WebSocket Authentication:**
- WebSocket connections require valid API key (initial HTTP upgrade includes Auth header)
- Users can only stream logs for their own executions (execution_id → account_id check)

**Log Privacy:**
- Logs may contain sensitive data (API keys printed to stdout)
- No cross-account log access (strict tenant isolation)

**Source:** Architecture security decisions

### Reliability/Availability

**Fault Tolerance:**
- **Network blips**: CLI auto-reconnects with cursor-based resumption (no duplicates/gaps)
- **API restart**: CLI reconnects, fetches historical logs from last cursor
- **Database unavailable**: Status/logs commands fail gracefully with clear error messages

**Log Guarantees:**
- Logs stored in database before streaming (durability)
- Sequence numbers ensure total ordering (no out-of-order delivery)
- Cursor-based resumption ensures exactly-once delivery (no duplicates)

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- WebSocket connection count (active streaming clients)
- Log throughput (lines/second)
- Average log latency (container → CLI)
- Status query p99 latency

**Logging:**
- API: WebSocket connections, disconnections, errors
- Runner: Log capture failures, streaming errors

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Python Dependencies:**
```toml
# cli/pyproject.toml
[tool.poetry.dependencies]
websockets = "^12.0"      # WebSocket client

# api/pyproject.toml
[tool.poetry.dependencies]
fastapi = "^0.104.0"      # WebSocket server (built-in)
redis = "^5.0.0"          # Pub/sub for log broadcasting (or in-memory event bus)
```

**Database Schema Updates:**
```sql
-- Execution logs table
CREATE TABLE execution_logs (
    log_id VARCHAR(64) PRIMARY KEY,
    execution_id VARCHAR(64) REFERENCES executions(execution_id),
    sequence_number INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    stream VARCHAR(16) NOT NULL,  -- 'stdout' | 'stderr'
    message TEXT NOT NULL
);

-- Composite primary key for efficient cursor queries
CREATE UNIQUE INDEX idx_execution_logs_cursor ON execution_logs(execution_id, sequence_number);

-- Index for timestamp ordering
CREATE INDEX idx_execution_logs_timestamp ON execution_logs(execution_id, timestamp);

-- Updates to executions table
ALTER TABLE executions ADD COLUMN started_at TIMESTAMP;
ALTER TABLE executions ADD COLUMN completed_at TIMESTAMP;
ALTER TABLE executions ADD COLUMN duration_seconds INT;
ALTER TABLE executions ADD COLUMN exit_code INT;
ALTER TABLE executions ADD COLUMN worker_hostname VARCHAR(128);
ALTER TABLE executions ADD COLUMN execution_metadata JSONB;
```

## Acceptance Criteria (Authoritative)

**AC-8.1: rgrid status Command**
1. When I run `rgrid status <exec_id>`, CLI displays execution status, duration, worker, cost
2. Status includes: status, started time, duration, worker hostname, exit code (if complete), artifacts count

**AC-8.2: rgrid logs Command (Historical)**
1. When I run `rgrid logs <exec_id>`, CLI fetches all logs from database
2. Logs displayed in chronological order with timestamps and stream (stdout/stderr)

**AC-8.3: WebSocket Log Streaming**
1. When I run `rgrid logs <exec_id> --follow`, CLI opens WebSocket connection to API
2. Logs stream in real-time (<1 second latency from container output)
3. Logs continue until execution completes or user cancels (Ctrl+C)

**AC-8.4: CLI Reconnection**
1. When WebSocket connection drops, CLI automatically reconnects within 5 seconds
2. CLI resumes streaming from last received sequence number (no duplicates, no gaps)

**AC-8.5: Batch Progress Display**
1. With `--watch` flag, CLI displays aggregate progress bar for batch
2. Progress shows: completed/failed/running/queued counts, ETA, cost
3. Progress updates every 2 seconds until batch completes

**AC-8.6: Execution Metadata Tracking**
1. Execution records include: started_at, completed_at, duration_seconds, exit_code, worker_hostname
2. Metadata stored in database and displayed in status command

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-8.1 | CLI: Status Command | cli/commands/status.py | Run execution, call status, verify all fields displayed |
| AC-8.2 | CLI: Logs Command | cli/commands/logs.py | Complete execution with logs, call logs, verify output |
| AC-8.3 | WebSocket Server | api/websocket/logs.py | Run with --follow, verify real-time log display |
| AC-8.4 | CLI Reconnection | cli/commands/logs.py | Simulate network drop, verify reconnection and resumption |
| AC-8.5 | CLI: Progress Tracker | cli/batch/progress.py | Run batch with --watch, verify progress bar updates |
| AC-8.6 | Metadata Tracker | api/services/metadata.py | Complete execution, verify metadata in database |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: WebSocket connections consume server resources (1000 concurrent = high memory)
   - **Mitigation**: Connection limits, auto-disconnect inactive clients after 1 hour
2. **R2**: Large executions (10M log lines) could bloat database
   - **Mitigation**: Log retention policy (30 days), same as artifacts
3. **R3**: Log latency >1s if API under load
   - **Mitigation**: Dedicated WebSocket workers, horizontal scaling

**Assumptions:**
1. **A1**: Most executions produce <100,000 log lines (typical for MVP workloads)
2. **A2**: Users tolerate 2-second progress polling (Epic 8 keeps for MVP, future: WebSocket)
3. **A3**: Network blips are rare (<1% of streaming sessions)

**Open Questions:**
1. **Q1**: Should we implement log search (grep across all executions)?
   - **Decision**: Deferred to post-MVP (requires full-text search index)
2. **Q2**: Should logs be compressed in database?
   - **Decision**: No in MVP (premature optimization), revisit if storage becomes issue

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Status formatting: Mock API response, verify CLI output format
   - Log parsing: Test sequence number assignment, timestamp formatting
   - Cursor logic: Test last_sequence tracking and resumption

2. **Integration Tests**
   - WebSocket streaming: Connect client, send log events, verify received
   - Database log storage: Insert logs, query with cursor, verify pagination
   - Reconnection: Disconnect client mid-stream, verify resume from cursor

3. **End-to-End Tests**
   - Complete flow: Run execution → call status → verify data
   - Real-time streaming: Run with --follow → verify logs appear in real-time
   - Batch progress: Run batch with --watch → verify progress bar updates

**Frameworks:**
- **WebSocket testing**: pytest-websocket, mock websocket server
- **CLI testing**: subprocess.run() to test actual CLI commands
- **Database**: pytest-postgresql for log queries

**Coverage of ACs:**
- AC-8.1: Integration test (call status, verify response)
- AC-8.2: E2E test (run execution, call logs, check output)
- AC-8.3: E2E test (run with --follow, verify real-time display)
- AC-8.4: Integration test (disconnect mid-stream, verify reconnect)
- AC-8.5: E2E test (run batch with --watch, check progress updates)
- AC-8.6: Integration test (complete execution, query metadata from DB)

**Edge Cases:**
- Execution with 0 logs (valid, no output)
- Execution with 1M logs (performance test, pagination)
- WebSocket disconnect before first log (reconnect immediately)
- Cursor > max sequence (no historical logs, start from real-time)
- Batch with 0 queued jobs (progress shows 100% immediately)

**Performance Tests:**
- WebSocket latency: Measure container → CLI time
- Status query latency: 1000 concurrent status requests
- Log query latency: Query 100,000 log lines with pagination

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 8.1
