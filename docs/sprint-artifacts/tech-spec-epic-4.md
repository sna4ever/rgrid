# Epic Technical Specification: Cloud Infrastructure (Hetzner)

Date: 2025-11-15
Author: BMad
Epic ID: 4
Status: Draft

---

## Overview

Epic 4 transforms RGrid from a static cluster to a fully elastic, auto-scaling platform by implementing intelligent worker provisioning and lifecycle management on Hetzner Cloud. This epic introduces the orchestrator service that monitors queue depth, provisions CX22 worker nodes on demand, manages billing-hour-aware termination for cost optimization, and handles automatic worker replacement on failure.

The implementation focuses on making infrastructure completely invisible to users while maintaining cost efficiency through smart provisioning algorithms and billing hour amortization. Workers are ephemeral (typical lifetime ~60 minutes per billing hour), provisioned only when needed, and automatically terminated when idle to minimize costs.

## Objectives and Scope

**In Scope:**
- Hetzner Cloud API integration for server provisioning (CX22 instances)
- Queue-based smart provisioning algorithm (provision only when truly needed)
- Worker lifecycle management (create, monitor, terminate)
- Billing hour awareness (keep workers alive until hour ends for cost efficiency)
- Cloud-init template for automatic worker configuration
- Docker image pre-pulling during worker initialization
- Worker auto-replacement on failure (dead worker detection → provision replacement)
- Cost tracking foundations (hourly cost, billing hour boundaries)

**Out of Scope:**
- Cost calculation and user billing (Epic 9)
- Manual worker scaling controls (MVP auto-scales only)
- Multi-region support (single region: Nuremberg/nbg1)
- Reserved instances or spot pricing
- Worker SSH access for debugging (future: Epic 10 ops tools)

## System Architecture Alignment

**Components Involved:**
- **Orchestrator (orchestrator/)**: Core service for provisioning, lifecycle management, health monitoring
- **Hetzner Cloud API**: REST API for server creation, deletion, status queries
- **Cloud-init**: Worker initialization script (install Docker, Ray, runner, join cluster)
- **Ray Cluster (Epic 3)**: Workers join cluster automatically on boot
- **Database (Postgres)**: Worker registry, billing hour tracking, cost metadata

**Architecture Constraints:**
- Workers are CX22 instances (2 vCPU, 4GB RAM, 40GB SSD)
- Single region deployment (Nuremberg/nbg1) for MVP
- Workers use Ubuntu 22.04 LTS base image
- Orchestrator runs as async daemon on control plane
- Provisioning respects account-level max worker limits (safety cap: 50 workers)
- Billing hour tracking per worker (Hetzner bills hourly, prorated)

**Cross-Epic Dependencies:**
- Requires Epic 1: Database schema, authentication
- Requires Epic 3: Ray cluster, worker heartbeat monitoring
- Enables Epic 5: Batch execution leverages auto-scaling
- Feeds Epic 9: Cost tracking uses billing hour data

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **Orchestrator Daemon** (`orchestrator/daemon.py`) | Main loop: check queue, provision/terminate workers, monitor health | Queue depth, worker heartbeats, billing hours | Provisioning/termination commands | Orchestrator Team |
| **Provisioner** (`orchestrator/provisioner.py`) | Create Hetzner servers via API, track provisioning status | Server config (type, region, cloud-init) | Worker metadata, server ID | Orchestrator Team |
| **Lifecycle Manager** (`orchestrator/lifecycle.py`) | Terminate idle/expired workers, enforce billing hour policy | Worker billing hour start, idle time | Termination commands | Orchestrator Team |
| **Queue Analyzer** (`orchestrator/queue.py`) | Calculate queue depth, estimate completion time, decide worker count | Executions table (queued jobs), worker capacity | Provision count (0 to N workers) | Orchestrator Team |
| **Cloud-Init Generator** (`infra/cloud-init/generator.py`) | Render cloud-init template with worker-specific config | Worker ID, control plane IP, API credentials | Cloud-init YAML script | Infra Team |
| **Cost Tracker** (`orchestrator/cost.py`) | Record hourly costs, track billing hour boundaries | Worker hourly rate, billing hour start | Cost metadata for Epic 9 | Orchestrator Team |

### Data Models and Contracts

**Worker Extended Schema (Updates to `workers` table):**
```python
class Worker(Base):
    __tablename__ = "workers"

    # ... existing fields from Epic 3 ...

    # Epic 4 additions:
    hetzner_server_id: int      # Hetzner Cloud server ID (from API)
    server_type: str            # e.g., "cx22" (2 vCPU, 4GB RAM)
    region: str                 # e.g., "nbg1" (Nuremberg)

    billing_hour_start: datetime  # When billing hour started (for cost tracking)
    hourly_cost_micros: int       # Cost in microns (€5.83/hr = 5,830,000 micros)

    provisioning_status: str      # provisioning|active|terminating|terminated
    provisioned_at: datetime      # When Hetzner API call succeeded
    active_at: datetime          # When worker joined Ray cluster
    idle_since: datetime         # When worker last executed a job (null if busy)

    # Termination metadata
    termination_reason: str      # billing_hour_end|idle|failed|manual
    terminated_at: datetime      # When worker was deleted
```

**Queue Metrics (Computed, Not Stored):**
```python
@dataclass
class QueueMetrics:
    """Real-time queue and capacity metrics."""
    queued_jobs: int              # count(status='queued')
    running_jobs: int             # count(status='running')

    total_workers: int            # count(status='active')
    idle_workers: int             # count(idle_since IS NOT NULL)
    available_slots: int          # sum(max_concurrent) - running_jobs

    avg_job_duration: float       # p50 of recent completed jobs (seconds)
    est_queue_clear_time: float   # queued_jobs / (available_slots / avg_job_duration)
```

**Provisioning Request:**
```python
@dataclass
class ProvisionRequest:
    """Request to provision N workers."""
    count: int                    # Number of workers to provision
    reason: str                   # "queue_depth" | "worker_replacement"
    server_type: str = "cx22"
    region: str = "nbg1"
    image: str = "ubuntu-22.04"
```

**Hetzner Cloud API Models:**
```python
# POST /servers (Hetzner API)
{
  "name": "rgrid-worker-abc123",
  "server_type": "cx22",
  "image": "ubuntu-22.04",
  "location": "nbg1",
  "user_data": "<cloud-init YAML>",
  "labels": {
    "app": "rgrid",
    "worker_id": "worker_abc123",
    "managed_by": "orchestrator"
  }
}

# Response
{
  "server": {
    "id": 12345678,
    "name": "rgrid-worker-abc123",
    "status": "initializing",  # → running after ~60s
    "public_net": {
      "ipv4": {"ip": "123.45.67.89"},
      "ipv6": {"ip": "2a01:..."}
    },
    "private_net": [
      {"ip": "10.0.1.5"}  # Ray uses private IP
    ]
  },
  "action": {
    "id": 87654321,
    "status": "running"  # → success when ready
  }
}
```

### APIs and Interfaces

**Orchestrator Loop (Pseudo-Code):**
```python
# orchestrator/daemon.py
async def orchestrator_loop():
    """
    Main orchestrator loop: provision, terminate, monitor.
    Runs every 10 seconds.
    """
    while True:
        # 1. Analyze queue and capacity
        metrics = await analyze_queue()

        # 2. Smart provisioning decision
        provision_count = calculate_provision_count(metrics)
        if provision_count > 0:
            await provision_workers(provision_count)

        # 3. Detect and replace failed workers
        dead_workers = await detect_dead_workers()  # Epic 3 logic
        if dead_workers:
            await provision_workers(len(dead_workers), reason="replacement")
            await terminate_workers(dead_workers)

        # 4. Terminate idle workers past billing hour
        expired_workers = await find_expired_workers()
        await terminate_workers(expired_workers, reason="billing_hour_end")

        # 5. Health checks and logging
        await log_cluster_state(metrics)

        await asyncio.sleep(10)  # 10-second loop
```

**Smart Provisioning Algorithm:**
```python
# orchestrator/queue.py
def calculate_provision_count(metrics: QueueMetrics) -> int:
    """
    Decide how many workers to provision based on queue depth.

    Algorithm (from architecture.md Decision 9):
    1. If available_slots >= queued_jobs → provision 0 (capacity sufficient)
    2. If est_queue_clear_time < 5 minutes → provision 0 (jobs completing soon)
    3. Else → provision ceil((queued_jobs - available_slots) / 2) workers
       (2 slots per worker, so divide deficit by 2)

    Returns:
        Number of workers to provision (0 to N)
    """
    # Case 1: Sufficient capacity
    if metrics.available_slots >= metrics.queued_jobs:
        return 0

    # Case 2: Jobs completing soon (within 5 minutes)
    if metrics.est_queue_clear_time < 300:  # 300 seconds = 5 minutes
        return 0

    # Case 3: Need more capacity
    deficit = metrics.queued_jobs - metrics.available_slots
    workers_needed = math.ceil(deficit / 2)  # 2 slots per CX22 worker

    # Safety cap: Don't provision more than 10 workers at once
    return min(workers_needed, 10)
```

**Billing Hour Termination Logic:**
```python
# orchestrator/lifecycle.py
async def find_expired_workers() -> List[Worker]:
    """
    Find workers that should be terminated:
    - Idle (no running jobs)
    - Past billing hour boundary (billing_hour_start + 60 minutes)

    Hetzner bills hourly, so maximize utilization within each hour.
    """
    now = datetime.utcnow()

    expired = await db.execute(
        """
        SELECT worker_id, billing_hour_start, idle_since
        FROM workers
        WHERE status = 'active'
          AND idle_since IS NOT NULL  -- Worker is idle
          AND billing_hour_start + INTERVAL '60 minutes' < NOW()
        """
    )

    return [Worker(**row) for row in expired]
```

**Worker Provisioning Implementation:**
```python
# orchestrator/provisioner.py
from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.locations.domain import Location

async def provision_workers(count: int, reason: str = "queue_depth"):
    """
    Provision N Hetzner CX22 workers.
    """
    hetzner_client = Client(token=HETZNER_API_TOKEN)

    for i in range(count):
        # 1. Generate worker ID
        worker_id = f"worker_{uuid.uuid4().hex[:12]}"

        # 2. Render cloud-init script
        cloud_init = render_cloud_init_template(
            worker_id=worker_id,
            control_plane_ip="10.0.0.1",
            ray_head_port=6379
        )

        # 3. Create Hetzner server
        response = hetzner_client.servers.create(
            name=f"rgrid-{worker_id}",
            server_type=ServerType(name="cx22"),
            image=Image(name="ubuntu-22.04"),
            location=Location(name="nbg1"),
            user_data=cloud_init,
            labels={"app": "rgrid", "worker_id": worker_id}
        )

        server = response.server
        action = response.action

        # 4. Create worker record
        await db.execute(
            """
            INSERT INTO workers (
                worker_id, hetzner_server_id, server_type, region,
                billing_hour_start, hourly_cost_micros,
                provisioning_status, provisioned_at
            ) VALUES (
                :worker_id, :server_id, 'cx22', 'nbg1',
                NOW(), 5830000,  -- €5.83/hr = 5,830,000 micros
                'provisioning', NOW()
            )
            """,
            {"worker_id": worker_id, "server_id": server.id}
        )

        logger.info(f"Provisioned worker {worker_id}, server ID {server.id}, reason: {reason}")

        # 5. Poll for server ready (background task)
        asyncio.create_task(wait_for_worker_ready(worker_id, server.id, action.id))
```

**Cloud-Init Template:**
```yaml
# infra/cloud-init/worker.yaml
#cloud-config
# RGrid Worker Bootstrap Script
# Generated by orchestrator for worker: {{worker_id}}

packages:
  - docker.io
  - python3-pip
  - python3-dev
  - build-essential

write_files:
  - path: /etc/rgrid/worker.conf
    content: |
      WORKER_ID={{worker_id}}
      CONTROL_PLANE_IP={{control_plane_ip}}
      RAY_HEAD_PORT={{ray_head_port}}
      DATABASE_URL={{database_url}}
      MINIO_ENDPOINT={{minio_endpoint}}

  - path: /etc/systemd/system/rgrid-runner.service
    content: |
      [Unit]
      Description=RGrid Runner Service
      After=network.target docker.service

      [Service]
      Type=simple
      User=root
      WorkingDir=/opt/rgrid
      ExecStart=/usr/bin/python3 /opt/rgrid/runner/main.py
      Restart=always
      EnvironmentFile=/etc/rgrid/worker.conf

      [Install]
      WantedBy=multi-user.target

runcmd:
  # Install Ray
  - pip3 install ray[default]==2.8.0
  - pip3 install docker boto3 sqlalchemy asyncpg

  # Pre-pull common Docker images (Epic 4 Story 4.4)
  - docker pull python:3.11-slim
  - docker pull python:3.10-slim
  - docker pull rgrid/python:3.11-datascience
  - docker pull rgrid/ffmpeg:latest

  # Start Ray worker
  - ray start --address={{control_plane_ip}}:{{ray_head_port}} --num-cpus=2 --memory=4294967296

  # Clone runner code (or download from artifact storage)
  - git clone https://github.com/rgrid/rgrid.git /opt/rgrid
  # OR: aws s3 cp s3://rgrid-artifacts/runner-latest.tar.gz /opt/rgrid/

  # Start runner service
  - systemctl daemon-reload
  - systemctl enable rgrid-runner.service
  - systemctl start rgrid-runner.service

  # Mark worker as active in database (via API call)
  - curl -X POST {{api_endpoint}}/internal/workers/{{worker_id}}/activate
```

### Workflows and Sequencing

**Worker Provisioning Flow:**
```
1. ORCHESTRATOR: Queue check (every 10 seconds)
   a. Query executions table: count(status='queued')
   b. Query workers table: sum(max_concurrent) - count(running jobs)
   c. Calculate metrics: queued_jobs=50, available_slots=10
   d. Smart provisioning: (50-10)/2 = 20 workers needed
   e. Safety cap: min(20, 10) = provision 10 workers

2. ORCHESTRATOR: Provision worker loop (10 times)
   a. Generate worker_id: worker_abc123
   b. Render cloud-init with worker_id, control plane IP
   c. Call Hetzner API: POST /servers
   d. Receive server_id: 12345678, status: initializing
   e. Create worker record: provisioning_status=provisioning
   f. Background task: poll action status

3. HETZNER: Server initialization (~60 seconds)
   a. Allocate compute resources (2 vCPU, 4GB RAM)
   b. Assign IP addresses (public + private 10.0.1.5)
   c. Boot Ubuntu 22.04 image
   d. Execute cloud-init script:
      - Install Docker, Python, Ray
      - Pre-pull Docker images (20 seconds)
      - Start Ray worker
      - Start runner service

4. WORKER: Runner startup
   a. Load config from /etc/rgrid/worker.conf
   b. Connect to database
   c. Call API: POST /internal/workers/{worker_id}/activate
   d. API updates worker: provisioning_status=active, active_at=NOW()
   e. Start heartbeat loop (every 30 seconds)

5. ORCHESTRATOR: Detect worker active (poll action status)
   a. Query Hetzner API: GET /actions/{action_id}
   b. Status: success (server booted)
   c. Verify worker in Ray cluster: ray.nodes()
   d. Log: "Worker worker_abc123 active after 62 seconds"

Total time: ~60-90 seconds from provision request to first job execution
```

**Billing Hour Termination Flow:**
```
1. ORCHESTRATOR: Billing hour check (every 10 seconds)
   a. Query workers:
      - status=active
      - idle_since IS NOT NULL (no running jobs)
      - billing_hour_start + 60 minutes < NOW()
   b. Find worker_abc123: billing_hour_start=10:00, now=11:05
      - Billing hour ended 5 minutes ago, worker idle
      - Candidate for termination

2. ORCHESTRATOR: Terminate worker
   a. Update worker: status=terminating, termination_reason=billing_hour_end
   b. Call Hetzner API: DELETE /servers/{server_id}
   c. Hetzner shuts down server (~5 seconds)
   d. Update worker: status=terminated, terminated_at=NOW()
   e. Worker removed from Ray cluster (detected in next heartbeat check)

3. COST TRACKING (Epic 9):
   a. Calculate worker lifetime: billing_hour_start to terminated_at
   b. Record cost: 1 hour × €5.83 = €5.83 = 5,830,000 micros
   c. Amortize cost across jobs executed during billing hour
```

**Worker Replacement Flow (Failure Scenario):**
```
1. WORKER FAILURE:
   a. Worker crashes (OOM, network disconnect)
   b. Worker stops sending heartbeats

2. ORCHESTRATOR: Dead worker detection (Epic 3 + Epic 4)
   a. Heartbeat monitor: last_heartbeat_at > 120 seconds ago
   b. Mark worker: status=dead, termination_reason=failed
   c. Reset running jobs: status=queued (Ray reschedules)
   d. Queue dead worker for termination

3. ORCHESTRATOR: Provision replacement (same loop iteration)
   a. calculate_provision_count() sees deficit (lost 2 slots)
   b. Provision 1 replacement worker
   c. New worker joins cluster within 60 seconds
   d. Queued jobs resume on new worker

4. ORCHESTRATOR: Clean up dead worker
   a. Call Hetzner API: DELETE /servers/{dead_worker_server_id}
   b. Update worker: status=terminated, terminated_at=NOW()
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Worker provisioning time**: < 90 seconds from orchestrator decision to first job execution
  - Hetzner API response: ~2 seconds
  - Server boot + cloud-init: ~60 seconds
  - Ray worker join: ~5 seconds
  - Runner service start: ~5 seconds
- **Orchestrator loop latency**: < 1 second per iteration (10-second interval)
- **Hetzner API rate limits**: 3600 requests/hour = 1 req/second sustained
  - Orchestrator respects limits (1 provision/terminate per second max)
- **Scale-up capacity**: 10 workers per loop (10 seconds × 10 workers = 100 workers/100 seconds)
- **Idle worker termination delay**: < 30 seconds after billing hour ends

**Scalability:**
- Support 100 concurrent workers (200 CPU slots)
- Orchestrator can manage 100 workers without performance degradation
- Hetzner account limit: 50 workers (safety cap, can request increase)

**Source:** Architecture performance targets, Hetzner API docs

### Security

**API Credentials:**
- Hetzner API token stored as environment variable (never in code)
- Token has scoped permissions: create/delete servers, read-only on other resources
- Token rotation policy: quarterly (manual process in MVP)

**Worker Access:**
- Workers have no SSH keys configured (no remote access by default)
- Cloud-init logs contain sensitive data (database URL, API keys)
  - Mitigation: Logs stored on worker, deleted on termination (not sent to Hetzner)

**Network Isolation:**
- Workers on private network (10.0.0.0/16)
- Only control plane accessible from internet (firewall rules)

**Source:** Architecture security decisions

### Reliability/Availability

**Fault Tolerance:**
- **Hetzner API failures**: Orchestrator retries with exponential backoff (max 3 retries)
- **Provisioning failures**: Log error, continue to next worker (don't crash orchestrator)
- **Worker boot failures**: Detect via heartbeat timeout (never joined cluster), terminate and retry
- **Billing hour edge case**: Worker provisioned at 10:59:30 → billing hour starts 10:59:30, terminates 11:59:30

**Graceful Degradation:**
- If Hetzner API unavailable: Stop provisioning, existing workers continue
- If database unavailable: Orchestrator pauses (can't query queue), logs error
- If control plane crashes: Workers continue running but can't join cluster (detected on reboot)

**Worker Lifetime Guarantees:**
- Workers live minimum 1 billing hour (maximize cost efficiency)
- Workers terminated only when idle (no running jobs)
- Workers with running jobs kept alive past billing hour (terminate after completion)

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Worker count by status (provisioning, active, terminating, terminated)
- Provisioning success rate (successful boots / total provision attempts)
- Average provisioning time (provision request → worker active)
- Billing hour utilization (jobs executed / max possible jobs per hour)
- Cost per worker (hourly cost × lifetime)
- Hetzner API error rate

**Logging:**
- Orchestrator: Provision decisions, termination events, API errors
- Cloud-init: Worker boot logs (accessible via Hetzner console)
- Worker: Heartbeat status, job execution count

**Alerts:**
- Hetzner API failure (3 consecutive errors)
- Worker provisioning timeout (>120 seconds without heartbeat)
- Account approaching worker limit (>80% of 50 workers)

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Hetzner Cloud Python SDK:**
```toml
# pyproject.toml - orchestrator
[tool.poetry.dependencies]
hcloud = "^1.33.0"           # Official Hetzner Cloud SDK
```

**Hetzner Cloud Resources:**
- **Server Type**: CX22 (2 vCPU, 4GB RAM, 40GB SSD, €5.83/month prorated hourly)
- **Region**: nbg1 (Nuremberg, Germany) - lowest latency for EU
- **Image**: ubuntu-22.04 (official Ubuntu image)
- **Network**: Private network 10.0.0.0/16 (pre-created, attached to all servers)

**Environment Variables (Orchestrator):**
```bash
HETZNER_API_TOKEN=<secret>         # API token from Hetzner Cloud console
HETZNER_NETWORK_ID=<network_id>    # Pre-created private network ID
RGRID_MAX_WORKERS=50               # Safety cap
RGRID_CONTROL_PLANE_IP=10.0.0.1
```

**Database Schema Updates:**
```sql
-- Updates to workers table (Epic 4 additions)
ALTER TABLE workers ADD COLUMN hetzner_server_id BIGINT;
ALTER TABLE workers ADD COLUMN server_type VARCHAR(32) DEFAULT 'cx22';
ALTER TABLE workers ADD COLUMN region VARCHAR(32) DEFAULT 'nbg1';
ALTER TABLE workers ADD COLUMN billing_hour_start TIMESTAMP;
ALTER TABLE workers ADD COLUMN hourly_cost_micros BIGINT DEFAULT 5830000;
ALTER TABLE workers ADD COLUMN provisioning_status VARCHAR(32) DEFAULT 'provisioning';
ALTER TABLE workers ADD COLUMN provisioned_at TIMESTAMP;
ALTER TABLE workers ADD COLUMN active_at TIMESTAMP;
ALTER TABLE workers ADD COLUMN idle_since TIMESTAMP;
ALTER TABLE workers ADD COLUMN termination_reason VARCHAR(64);

-- Index for billing hour queries
CREATE INDEX idx_workers_billing_hour ON workers(billing_hour_start, idle_since);

-- Index for provisioning status
CREATE INDEX idx_workers_provisioning_status ON workers(provisioning_status);
```

**Integration Points:**
- Orchestrator → Hetzner API: REST over HTTPS (hcloud SDK)
- Cloud-init → Control Plane: Worker activation callback (HTTP POST)
- Orchestrator → Database: Worker registry, queue metrics
- Orchestrator → Ray: Cluster state queries (ray.nodes())

## Acceptance Criteria (Authoritative)

**AC-4.1: Hetzner Worker Provisioning**
1. Orchestrator calls Hetzner API to create CX22 server in nbg1
2. Server uses cloud-init script with worker_id, control plane IP
3. Worker joins Ray cluster within 60 seconds
4. Worker record created in database with hetzner_server_id, billing_hour_start

**AC-4.2: Smart Provisioning Algorithm**
1. If available_slots >= queued_jobs, provision 0 workers
2. If est_queue_clear_time < 5 minutes, provision 0 workers
3. Else, provision ceil((queued_jobs - available_slots) / 2) workers
4. Orchestrator respects max_workers=50 cap

**AC-4.3: Billing Hour Termination**
1. Workers kept alive until billing_hour_start + 60 minutes
2. When billing hour ends and worker is idle, orchestrator terminates worker
3. Workers with running jobs kept alive past billing hour (terminate after completion)
4. Termination updates worker: status=terminated, termination_reason=billing_hour_end

**AC-4.4: Docker Image Pre-Pulling**
1. Cloud-init script pre-pulls: python:3.11-slim, python:3.10-slim, datascience, ffmpeg
2. Images cached locally on worker before runner service starts
3. First execution using pre-pulled runtime has minimal cold-start latency

**AC-4.5: Worker Auto-Replacement**
1. When worker is detected as dead (no heartbeat >120s), orchestrator provisions replacement
2. Replacement worker joins cluster and receives rescheduled jobs
3. Dead worker terminated via Hetzner API

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-4.1 | Services: Provisioner | orchestrator/provisioner.py, Hetzner API | Mock Hetzner API, verify POST /servers called with correct params |
| AC-4.2 | APIs: Smart Provisioning | orchestrator/queue.py | Unit test with various queue/capacity scenarios, verify provision count |
| AC-4.3 | Services: Lifecycle Manager | orchestrator/lifecycle.py | Simulate worker past billing hour, verify termination |
| AC-4.4 | Cloud-Init Template | infra/cloud-init/worker.yaml | Boot real worker, verify docker images cached, measure first execution time |
| AC-4.5 | Workflows: Worker Replacement | orchestrator/daemon.py | Simulate worker failure, verify replacement provisioned and dead worker terminated |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Hetzner API outage prevents new workers from provisioning
   - **Mitigation**: Existing workers continue, queue backs up temporarily (acceptable for MVP)
2. **R2**: Cloud-init failure leaves worker in "provisioning" limbo (never joins cluster)
   - **Mitigation**: Timeout detection (if no heartbeat after 120s, terminate and retry)
3. **R3**: Billing hour logic bug could over/under-terminate workers
   - **Mitigation**: Comprehensive unit tests, monitoring for cost anomalies
4. **R4**: Worker provisioning cost (~€5.83/hr each) could accumulate if queue miscalculated
   - **Mitigation**: Max worker cap (50), cost alerts in Epic 9

**Assumptions:**
1. **A1**: Hetzner CX22 availability in nbg1 region (generally high availability)
2. **A2**: Cloud-init always executes (Ubuntu 22.04 standard feature)
3. **A3**: Worker provisioning time consistent (~60-90s, barring Hetzner issues)
4. **A4**: Hetzner API token does not expire (valid until manually rotated)
5. **A5**: Private network (10.0.0.0/16) pre-created and attached to servers

**Open Questions:**
1. **Q1**: Should we support multiple regions for lower latency?
   - **Decision**: Deferred to post-MVP (single region nbg1 sufficient)
2. **Q2**: What if Hetzner introduces new pricing (e.g., per-second billing)?
   - **Decision**: Update hourly_cost_micros and billing logic (config-driven)
3. **Q3**: Should orchestrator run as separate process or part of API?
   - **Decision**: Separate process (easier to scale, debug, restart independently)
4. **Q4**: How to handle Hetzner account rate limits (3600 req/hr)?
   - **Decision**: Orchestrator throttles (1 provision/terminate per second max)

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Provisioner: Mock Hetzner API, verify POST /servers request format
   - Queue analyzer: Test smart provisioning algorithm with various scenarios
   - Lifecycle manager: Test billing hour termination logic with edge cases

2. **Integration Tests**
   - Hetzner API: Real API calls to create/delete test servers
   - Cloud-init: Boot real server, verify Ray worker joins cluster
   - Orchestrator loop: Full cycle (provision → active → terminate)

3. **End-to-End Tests**
   - Complete flow: Submit 100 jobs → orchestrator provisions workers → execute → terminate
   - Billing hour: Provision worker at T, submit jobs, verify kept alive until T+60m
   - Worker replacement: Kill worker, verify replacement provisioned and jobs rescheduled

**Frameworks:**
- **Hetzner API**: pytest with hcloud SDK, test account with limited budget
- **Cloud-init**: Packer or Terraform for testing worker images
- **Orchestrator**: pytest-asyncio, mock database and Hetzner client

**Coverage of ACs:**
- AC-4.1: Integration test (real Hetzner API call, verify worker boots)
- AC-4.2: Unit test (mock queue metrics, verify provision count)
- AC-4.3: Unit test (billing hour logic), E2E test (real worker lifecycle)
- AC-4.4: Integration test (boot worker, check docker images cached)
- AC-4.5: E2E test (simulate worker failure, verify replacement)

**Edge Cases:**
- Worker provisioned at 10:59:55 (billing hour starts immediately, ends 11:59:55)
- Queue depth spikes from 0 to 1000 (should provision max 10 workers per loop)
- Hetzner API returns 429 rate limit (orchestrator backs off)
- Worker never sends heartbeat (timeout after 120s, terminate and retry)
- All workers at max capacity (50), queue continues to grow (acceptable, wait for idle workers)

**Performance Tests:**
- Measure provisioning time: 100 iterations, track p50/p95/p99
- Orchestrator loop latency: Verify <1s per iteration with 50 workers
- Billing hour accuracy: Verify termination within 30s of billing hour end

**Cost Testing:**
- Provision 10 workers, run for 10 minutes, verify cost calculation matches Hetzner bill
- Test cost amortization: 10 jobs in 1 hour on 1 worker → €5.83 / 10 = €0.58 per job

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 4.1
