# Epic Technical Specification: Distributed Orchestration (Ray)

Date: 2025-11-15
Author: BMad
Epic ID: 3
Status: Draft

---

## Overview

Epic 3 introduces distributed task orchestration using Ray, transforming RGrid from a single-runner system to a horizontally scalable platform capable of executing jobs across multiple worker nodes. This epic establishes the Ray cluster architecture with a head node on the control plane and worker nodes on Hetzner CX22 instances, enabling parallel execution and fault-tolerant task distribution.

By integrating Ray as the distributed execution framework, this epic unlocks the foundation for batch operations (Epic 5), auto-scaling infrastructure (Epic 4), and multi-tenant workload isolation. The implementation focuses on cluster setup, worker registration, task submission patterns, and basic health monitoring to detect and handle worker failures.

## Objectives and Scope

**In Scope:**
- Ray head node deployment on control plane (single head, persistent)
- Ray worker initialization on each Hetzner worker node (dynamic workers)
- Execution submission as Ray remote tasks (@ray.remote pattern)
- Task scheduling and distribution across available workers
- Worker heartbeat monitoring and dead worker detection
- Basic worker health tracking (last_heartbeat_at in database)
- Ray dashboard for cluster visibility

**Out of Scope:**
- Auto-provisioning of Hetzner workers (Epic 4)
- Worker lifecycle management and termination (Epic 4)
- Advanced fault tolerance (job retries, Epic 10)
- Ray autoscaler integration (manual scaling in Epic 3)
- Multi-tenancy enforcement (all workers share cluster in Epic 3)
- Cost tracking per worker (Epic 9)

## System Architecture Alignment

**Components Involved:**
- **Ray Head Node**: Central coordinator on control plane (port 6379, dashboard 8265)
- **Ray Workers**: Agent processes on each Hetzner node (join cluster on startup)
- **API (api/)**: Submits executions as Ray tasks instead of direct runner invocation
- **Orchestrator (orchestrator/)**: Monitors worker heartbeats, detects failures (Epic 4 adds provisioning)
- **Runner (runner/)**: Now executes as Ray task function, reports heartbeats
- **Database (Postgres)**: Tracks worker_heartbeats, worker registry

**Architecture Constraints:**
- Ray cluster uses hardcoded control plane IP (10.0.0.1:6379) for worker discovery
- Single Ray head node (no HA in MVP, acceptable risk per architecture)
- Workers advertise max_concurrent=2 (1 job per vCPU on CX22: 2 vCPU)
- Ray uses Redis protocol for cluster state (port 6379)
- Execution flow changes from API → Runner to API → Ray → Runner

**Cross-Epic Dependencies:**
- Requires Epic 1: API infrastructure, database schema
- Requires Epic 2: Runner execution logic (now wrapped in Ray task)
- Enables Epic 4: Worker provisioning/termination uses Ray cluster membership
- Enables Epic 5: Batch execution leverages Ray parallel task submission

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **Ray Head Service** (`control-plane/ray-head.py`) | Initialize Ray head node, serve dashboard, coordinate workers | Cluster config (port, dashboard port) | Ray cluster endpoint (10.0.0.1:6379) | Infra Team |
| **Ray Worker Agent** (`runner/ray_worker.py`) | Connect to head node, register resources, receive task assignments | Head node address (10.0.0.1:6379) | Worker ID, resource availability | Runner Team |
| **Task Executor** (`runner/executor.py`) | Execute script as Ray remote task (wrapped from Epic 2) | Execution ID (from Ray task param) | ExecutionResult (exit code, logs) | Runner Team |
| **Orchestrator Heartbeat Monitor** (`orchestrator/heartbeat.py`) | Poll worker_heartbeats table, detect dead workers | Heartbeat timeout threshold (120s) | Dead worker IDs, reschedule signals | Orchestrator Team |
| **API Ray Client** (`api/services/ray_client.py`) | Submit executions as Ray tasks, track task IDs | Execution record | Ray task ID (ObjectRef) | API Team |
| **Worker Registry** (`orchestrator/worker_registry.py`) | Track active workers, sync with Ray cluster state | Ray cluster membership | Worker metadata (ID, node, status) | Orchestrator Team |

### Data Models and Contracts

**Worker Registry (Postgres `workers` table):**
```python
class Worker(Base):
    __tablename__ = "workers"

    worker_id: str           # Primary key, format: worker_{uuid}
    node_id: str            # Hetzner server ID (from cloud API)
    ray_node_id: str        # Ray internal node ID
    ip_address: str         # Private IP (e.g., 10.0.1.5)
    max_concurrent: int     # Resource slots (2 for CX22)

    status: str             # active|dead|terminating
    created_at: datetime    # Worker provisioned timestamp
    terminated_at: datetime # Worker shutdown timestamp (null if active)

    # Epic 4 additions:
    # billing_hour_start: datetime
    # hourly_cost_micros: int
```

**Worker Heartbeat (Postgres `worker_heartbeats` table):**
```python
class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: str          # Foreign key to workers
    last_heartbeat_at: datetime  # Updated every 30 seconds
    ray_available_resources: dict  # JSON: {CPU: 2, memory: 4GB, custom_resources}

    # Primary key: worker_id (upsert pattern)
```

**Execution Record Updates:**
```python
# New fields added to executions table from Epic 2:
class Execution(Base):
    # ... existing fields from Epic 2 ...

    ray_task_id: str       # Ray ObjectRef ID for tracking
    worker_id: str         # Which worker executed this job (FK to workers)

    # Epic 3 adds worker tracking for execution history
```

**Ray Task Function Signature:**
```python
# runner/tasks.py
@ray.remote
def execute_script(execution_id: str) -> dict:
    """
    Ray remote task wrapper for script execution.

    Args:
        execution_id: Execution record primary key

    Returns:
        dict with keys: exit_code, status, artifacts_uploaded, error (if any)

    Execution flow:
    1. Load execution from database
    2. Download inputs from MinIO
    3. Run Docker container (Epic 2 logic)
    4. Upload outputs
    5. Update execution status
    6. Return result
    """
    pass  # Implementation reuses Epic 2 executor.py logic
```

### APIs and Interfaces

**Ray Head Node Endpoints:**
```
# Ray Head Node (Control Plane)
TCP 6379: Ray cluster coordination (Redis protocol)
TCP 8265: Ray Dashboard (web UI)

# Worker connection:
ray.init(address="10.0.0.1:6379")
```

**API → Ray Task Submission:**
```python
# api/services/ray_client.py
import ray

class RayExecutionService:
    async def submit_execution(self, execution: Execution) -> str:
        """
        Submit execution as Ray remote task.

        Args:
            execution: Execution record with script, args, runtime

        Returns:
            Ray task ID (ObjectRef hex string)

        Raises:
            RayConnectionError: If Ray head node unavailable
        """
        # Initialize Ray client (singleton connection pool)
        if not ray.is_initialized():
            ray.init(address="10.0.0.1:6379", namespace="rgrid")

        # Import remote task function
        from runner.tasks import execute_script

        # Submit task (non-blocking)
        task_ref = execute_script.remote(execution.execution_id)

        # Store ObjectRef for tracking
        execution.ray_task_id = task_ref.hex()
        await db.commit()

        return task_ref.hex()
```

**Worker Heartbeat API:**
```python
# runner/ray_worker.py - Heartbeat loop
async def send_heartbeat():
    """
    Send heartbeat to database every 30 seconds.
    """
    while True:
        async with db.session() as session:
            await session.execute(
                """
                INSERT INTO worker_heartbeats (worker_id, last_heartbeat_at, ray_available_resources)
                VALUES (:worker_id, NOW(), :resources)
                ON CONFLICT (worker_id) DO UPDATE SET
                    last_heartbeat_at = NOW(),
                    ray_available_resources = EXCLUDED.ray_available_resources
                """,
                {
                    "worker_id": WORKER_ID,
                    "resources": ray.available_resources()  # {CPU: 1.5, memory: 3GB}
                }
            )
        await asyncio.sleep(30)
```

**Orchestrator Dead Worker Detection:**
```python
# orchestrator/heartbeat.py
async def detect_dead_workers():
    """
    Find workers with stale heartbeats (>120 seconds).
    Mark as dead and reschedule orphaned jobs.
    """
    dead_workers = await db.execute(
        """
        SELECT worker_id FROM worker_heartbeats
        WHERE last_heartbeat_at < NOW() - INTERVAL '120 seconds'
        """
    )

    for worker_id in dead_workers:
        # Mark worker as dead
        await db.execute(
            "UPDATE workers SET status='dead', terminated_at=NOW() WHERE worker_id=:id",
            {"id": worker_id}
        )

        # Find orphaned executions (status=running, worker_id=dead_worker)
        orphaned = await db.execute(
            """
            UPDATE executions SET status='queued', worker_id=NULL
            WHERE worker_id=:id AND status='running'
            RETURNING execution_id
            """,
            {"id": worker_id}
        )

        # Ray will auto-reschedule tasks to other workers (no manual intervention)
        logger.info(f"Rescheduled {len(orphaned)} orphaned tasks from {worker_id}")
```

### Workflows and Sequencing

**Ray Cluster Initialization (Control Plane Startup):**
```
1. Control Plane Boot:
   a. Start Ray head node: ray start --head --port=6379 --dashboard-port=8265
   b. Ray allocates shared memory, initializes Redis
   c. Dashboard starts on http://10.0.0.1:8265
   d. Head node ready, listening for worker connections

2. Worker Node Boot (Hetzner CX22 via cloud-init):
   a. Install Docker, Python, ray package
   b. Start Ray worker: ray start --address=10.0.0.1:6379 --num-cpus=2 --memory=4GB
   c. Worker registers with head node
   d. Worker ID assigned by Ray (e.g., node:10.0.1.5)
   e. Worker visible in Ray dashboard

3. Worker Registry Sync:
   a. Runner on worker queries Ray node ID: ray.get_runtime_context().node_id
   b. Runner creates worker record in database:
      - worker_id: generated UUID
      - ray_node_id: from Ray
      - ip_address: from cloud-init metadata
      - max_concurrent: 2
      - status: active
   c. Runner starts heartbeat loop (every 30s)
```

**Execution Flow (API → Ray → Runner):**
```
1. USER: rgrid run script.py (same as Epic 2)

2. CLI → API: POST /api/v1/executions (unchanged from Epic 2)

3. API (NEW LOGIC):
   a. Create execution record (status=queued)
   b. Generate presigned input upload URLs
   c. Submit Ray task:
      task_ref = execute_script.remote(execution.execution_id)
   d. Store ray_task_id in execution record
   e. Return execution_id to CLI

4. RAY SCHEDULER (NEW STEP):
   a. Ray selects worker with available CPU slot
   b. Ray assigns task to worker node
   c. Worker receives task parameters (execution_id)

5. RUNNER ON WORKER (Epic 2 logic wrapped in Ray task):
   a. Task function: execute_script(execution_id) starts
   b. Update execution: status=running, worker_id=<current worker>
   c. Download inputs from MinIO
   d. Run Docker container (Epic 2 container execution)
   e. Capture exit code, logs
   f. Upload outputs to MinIO
   g. Update execution: status=completed|failed, exit_code
   h. Return {exit_code, status} to Ray

6. RAY TASK COMPLETION:
   a. Ray marks task as complete
   b. Frees CPU slot on worker (available for next task)
   c. Result stored in Ray's object store (not used in Epic 3, future: Epic 8 can stream results)

7. ORCHESTRATOR (Background Loop):
   a. Every 30s: Check worker heartbeats
   b. If worker missing for >120s: Mark dead, reschedule running tasks
```

**Worker Failure Scenario:**
```
1. Worker crashes (e.g., OOM, network disconnect)
2. Worker stops sending heartbeats
3. Orchestrator detects stale heartbeat (>120s)
4. Orchestrator marks worker as dead
5. Orchestrator finds executions with status=running, worker_id=dead_worker
6. Orchestrator resets executions to status=queued, worker_id=NULL
7. API resubmits Ray tasks (or Ray auto-retries if task policy set)
8. Ray schedules tasks to healthy workers
9. Execution completes on new worker
```

**Sequence Diagram (Text):**
```
User → CLI: rgrid run script.py
CLI → API: POST /executions
API → DB: INSERT execution (status=queued)
API → Ray Head: submit execute_script.remote(exec_id)
Ray Head → Ray Worker: assign task to worker with CPU slot
Ray Worker → Runner: execute_script(exec_id) invoked
Runner → DB: UPDATE execution (status=running, worker_id)
Runner → Docker: run container (Epic 2 logic)
Docker → Runner: exit_code, logs
Runner → MinIO: upload outputs
Runner → DB: UPDATE execution (status=completed)
Runner → Ray Worker: return result
Ray Worker → Ray Head: task complete
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Task scheduling latency**: < 500ms from task submission to worker assignment
  - Ray scheduler overhead: ~100ms
  - Network RTT (API → Ray head): ~50ms
- **Worker registration time**: < 5 seconds from `ray start` to cluster membership
- **Heartbeat overhead**: < 10ms database write every 30 seconds per worker
- **Dead worker detection**: Within 150 seconds (120s timeout + 30s check interval)
- **Cluster capacity**: Support 100 concurrent workers (200 CPU slots at 2 per worker)
  - Ray head node on 4 vCPU control plane can coordinate 100+ workers

**Scalability:**
- Ray head node memory usage: ~1GB + 10MB per worker (100 workers = 2GB total)
- Task throughput: 1000 tasks/minute (limited by worker count, not Ray overhead)
- Ray object store: Not used in Epic 3 (future: store logs, intermediate results)

**Source:** Ray documentation, architecture NFR targets

### Security

**Cluster Isolation:**
- Ray cluster runs on private network (10.0.0.0/16)
- Head node not exposed to public internet (firewall rule)
- Workers connect via internal IPs only

**Authentication:**
- No Ray authentication in Epic 3 (all workers trusted, same tenant)
- Future: Ray client authentication with shared secret or mTLS

**Task Execution:**
- Tasks run with same isolation as Epic 2 (Docker containers, no network)
- Ray task code is trusted (bundled with runner, not user-provided)

**Source:** Architecture security decisions

### Reliability/Availability

**Fault Tolerance:**
- **Worker failures**: Detected via heartbeat, tasks automatically rescheduled
- **Head node failure**: Cluster unavailable, requires manual restart (no HA in MVP)
  - Mitigation: Control plane on stable instance, monitoring alerts
- **Task failures**: Ray logs error, execution marked as failed (no auto-retry in Epic 3, added in Epic 10)

**Heartbeat Guarantees:**
- At-least-once heartbeat delivery (worker retries on database timeout)
- Stale heartbeat threshold: 120 seconds (2 missed heartbeats)
- False positives: Network blip could trigger dead worker detection (acceptable tradeoff)

**Task Assignment:**
- Ray guarantees task runs on exactly one worker (no duplicate execution)
- If worker dies mid-task: Ray reschedules to another worker (at-most-once semantic)

**Source:** Ray fault tolerance docs, architecture reliability patterns

### Observability

**Ray Dashboard:**
- Web UI on http://10.0.0.1:8265 (internal access only)
- Displays: Active workers, CPU/memory usage, task queue depth, completed tasks
- Useful for debugging cluster state, capacity planning

**Metrics:**
- Worker count (active, dead, total provisioned)
- Task queue depth (waiting for CPU slot)
- Task completion rate (tasks/minute)
- Worker CPU utilization (from ray.available_resources())
- Heartbeat lag (time since last heartbeat per worker)

**Logging:**
- Ray head logs: Worker join/leave events, task submissions, errors
- Runner logs: Task start/stop, execution ID, worker ID
- Orchestrator logs: Dead worker detection, reschedule events

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Ray Framework:**
```toml
# pyproject.toml additions
[tool.poetry.dependencies]
ray = "^2.8.0"              # Core Ray library
ray[default] = "^2.8.0"     # Includes dashboard dependencies
```

**Infrastructure:**
- **Control Plane**: Single instance (4 vCPU, 8GB RAM recommended)
  - Runs Ray head node as systemd service
  - Accessible at static IP 10.0.0.1 (private network)
- **Worker Nodes**: Hetzner CX22 (2 vCPU, 4GB RAM)
  - Ray worker installed via cloud-init script
  - Auto-connects to head node on boot

**Network Configuration:**
- **Firewall Rules**:
  - Control plane: Allow inbound 6379 (Ray) from 10.0.0.0/16
  - Control plane: Allow inbound 8265 (dashboard) from admin IPs only
  - Workers: Allow outbound to control plane 6379

**Database Schema Updates:**
```sql
-- New table: workers
CREATE TABLE workers (
    worker_id VARCHAR(64) PRIMARY KEY,
    node_id VARCHAR(128),
    ray_node_id VARCHAR(128),
    ip_address INET,
    max_concurrent INT DEFAULT 2,
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    terminated_at TIMESTAMP
);

-- New table: worker_heartbeats
CREATE TABLE worker_heartbeats (
    worker_id VARCHAR(64) PRIMARY KEY REFERENCES workers(worker_id),
    last_heartbeat_at TIMESTAMP DEFAULT NOW(),
    ray_available_resources JSONB
);

-- Index for dead worker detection
CREATE INDEX idx_heartbeats_last ON worker_heartbeats(last_heartbeat_at);

-- Update executions table
ALTER TABLE executions ADD COLUMN ray_task_id VARCHAR(128);
ALTER TABLE executions ADD COLUMN worker_id VARCHAR(64) REFERENCES workers(worker_id);
```

**Cloud-Init Template (Partial):**
```yaml
# infra/cloud-init/worker.yaml
#cloud-config
packages:
  - docker.io
  - python3-pip

runcmd:
  - pip3 install ray[default]==2.8.0
  - ray start --address=10.0.0.1:6379 --num-cpus=2 --memory=4294967296
  - systemctl start rgrid-runner.service
```

**Integration Points:**
- API → Ray Head: Python `ray.init()` client
- Workers → Ray Head: Ray cluster protocol (TCP 6379)
- Runner → Database: Worker registry, heartbeat updates
- Orchestrator → Ray Head: Query cluster state via `ray.nodes()` API

## Acceptance Criteria (Authoritative)

**AC-3.1: Ray Head Node Setup**
1. Ray head node starts on control plane boot
2. Dashboard accessible at http://10.0.0.1:8265
3. Workers can connect via `ray start --address=10.0.0.1:6379`

**AC-3.2: Ray Worker Initialization**
1. When Hetzner worker boots, Ray worker connects to head node
2. Worker registers with max_concurrent=2 (2 CPU slots)
3. Worker visible in Ray dashboard
4. Worker record created in database with status=active

**AC-3.3: Submit Executions as Ray Tasks**
1. API submits executions via `execute_script.remote(execution_id)`
2. Ray schedules task to worker with available CPU slot
3. Runner executes script (Epic 2 logic)
4. Execution record updated with worker_id and ray_task_id

**AC-3.4: Worker Health Monitoring**
1. Workers send heartbeat every 30 seconds to database
2. Orchestrator detects workers with no heartbeat for >120 seconds
3. Dead workers marked as status=dead
4. Running executions on dead workers reset to status=queued and rescheduled

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-3.1 | Services: Ray Head Service | control-plane/ray-head.py | Start control plane, verify Ray dashboard accessible, check worker can connect |
| AC-3.2 | Services: Ray Worker Agent | runner/ray_worker.py, workers table | Boot worker node, verify Ray connection, check database worker record |
| AC-3.3 | APIs: Ray Task Submission | api/services/ray_client.py | Submit execution via API, verify Ray task created, check worker_id populated |
| AC-3.4 | Services: Heartbeat Monitor | orchestrator/heartbeat.py | Simulate worker heartbeat stop, verify orchestrator marks dead, check rescheduling |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Single Ray head node is single point of failure
   - **Mitigation**: Control plane on stable instance, monitoring alerts, manual restart SOP (HA deferred to post-MVP)
2. **R2**: Hardcoded head node IP (10.0.0.1) couples workers to control plane
   - **Mitigation**: Acceptable for MVP, future: use DNS or service discovery
3. **R3**: Ray memory overhead (1GB+ for head node) on 4 vCPU control plane
   - **Mitigation**: Monitor memory usage, upgrade control plane if needed (unlikely for 100 workers)
4. **R4**: Dead worker detection lag (120s) means ~2 minutes of hung executions
   - **Mitigation**: Acceptable for MVP, user can manually retry (Epic 10)

**Assumptions:**
1. **A1**: Control plane has static private IP (10.0.0.1)
2. **A2**: Workers have network access to control plane on port 6379
3. **A3**: Ray 2.8+ is stable for production (mature project, widely used)
4. **A4**: All workers trust head node (no malicious workers in single-tenant MVP)
5. **A5**: Workers don't need graceful shutdown (terminate immediately on failure)

**Open Questions:**
1. **Q1**: Should we use Ray autoscaler or custom orchestrator for worker provisioning?
   - **Decision**: Custom orchestrator (Epic 4) for cost control, Ray autoscaler is opinionated
2. **Q2**: How to handle Ray head node upgrades without downtime?
   - **Decision**: Deferred, accept downtime for MVP (schedule maintenance window)
3. **Q3**: Should Ray object store be used for logs/outputs?
   - **Decision**: No, use MinIO for consistency (Ray object store is ephemeral)
4. **Q4**: What happens if database is down when heartbeat fires?
   - **Decision**: Worker retries with exponential backoff, logs error (don't crash worker)

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Ray client: Task submission, ObjectRef tracking
   - Heartbeat monitor: Dead worker detection logic
   - Worker registry: Create, update, query worker records

2. **Integration Tests**
   - Ray cluster: Head node + 2 workers, submit task, verify execution
   - Heartbeat: Worker sends heartbeat, verify database update
   - Dead worker: Stop heartbeat, verify orchestrator marks dead

3. **End-to-End Tests**
   - Complete flow: Start cluster → submit execution → verify runs on worker → check heartbeat
   - Worker failure: Kill worker mid-execution → verify dead detection → verify rescheduling
   - Cluster scale: 10 workers, 20 concurrent executions, verify all complete

**Frameworks:**
- **Ray**: ray.init() in test mode (local cluster)
- **Database**: pytest-postgresql (ephemeral test database)
- **Docker**: For E2E tests, use docker-compose to simulate cluster

**Coverage of ACs:**
- AC-3.1: Unit test (mock Ray head), E2E test (real cluster)
- AC-3.2: Integration test (worker connects to test head)
- AC-3.3: Integration test (submit task, verify execution)
- AC-3.4: Unit test (heartbeat logic), integration test (simulate dead worker)

**Edge Cases:**
- Worker crashes before sending first heartbeat (never registered)
- Worker crashes mid-task (task rescheduled, outputs lost)
- Head node crashes (all workers disconnect, cluster unavailable)
- Database unavailable during heartbeat (worker retries, logs error)
- Two workers with same IP (should not happen, but detect and alert)

**Performance Tests:**
- Task scheduling latency: Submit 100 tasks, measure p99 assignment time
- Heartbeat overhead: Measure database write time under load (100 workers)
- Dead worker detection: Time from heartbeat stop to reschedule

**Mocking Strategy:**
- Unit tests: Mock ray.remote(), ray.init()
- Integration tests: Real Ray cluster (local mode)
- E2E tests: Real Ray cluster (docker-compose with control plane + workers)

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 3.1
