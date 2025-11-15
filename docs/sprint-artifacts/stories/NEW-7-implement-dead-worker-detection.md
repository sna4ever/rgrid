# Story NEW-7: Implement Dead Worker Detection

Status: ready-for-dev (Deferred from Tier 3 - Complex infrastructure)

## Story

As a platform operator,
I want dead workers to be detected automatically,
So that jobs from crashed workers are marked as failed and can be retried.

## Acceptance Criteria

1. **Given** a worker is running and processing jobs
2. **When** the worker crashes or becomes unresponsive
3. **Then** the system detects the dead worker and handles it:
   - Worker sends heartbeat every 30 seconds to database
   - Separate cleanup process checks for stale heartbeats
   - Workers with heartbeat older than 2 minutes marked as dead
   - All "running" jobs from dead worker marked as "failed"
   - Clear error message: "Worker died unexpectedly"
   - Jobs can be manually or automatically retried

## Tasks / Subtasks

- [ ] Task 1: Implement worker heartbeat (AC: #1)
  - [ ] Create `worker_heartbeats` table in database
  - [ ] Add heartbeat loop to worker process
  - [ ] Send heartbeat every 30 seconds
  - [ ] Store worker_id, last_seen timestamp
  - [ ] Handle database connection failures gracefully

- [ ] Task 2: Implement cleanup process (AC: #2, #3)
  - [ ] Create separate cleanup daemon/cron job
  - [ ] Query for stale heartbeats (> 2 minutes old)
  - [ ] Mark workers as "dead" in database
  - [ ] Log dead worker detection events

- [ ] Task 3: Handle dead worker jobs (AC: #4, #5)
  - [ ] Query for jobs with status "running" from dead workers
  - [ ] Update job status to "failed"
  - [ ] Set error message: "Worker died unexpectedly"
  - [ ] Optionally trigger retry mechanism

- [ ] Task 4: Testing and monitoring (AC: #6)
  - [ ] Integration test: Kill worker, verify detection
  - [ ] Test jobs marked as failed within 2 minutes
  - [ ] Add monitoring/alerting for dead workers
  - [ ] Document worker recovery procedures

## Dev Notes

### Prerequisites

- Worker process exists (Story 2-2)
- Database models for executions (Story 1-6)
- Job status tracking (Stories 8-1, 8-2)

### Technical Notes

**Database Schema**:
```sql
CREATE TABLE worker_heartbeats (
    worker_id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255),
    last_seen TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_heartbeats_last_seen ON worker_heartbeats(last_seen);
```

**Heartbeat Logic**:
```python
# In worker process
async def send_heartbeat():
    while True:
        await db.execute(
            "INSERT INTO worker_heartbeats (worker_id, hostname, last_seen) "
            "VALUES (:worker_id, :hostname, NOW()) "
            "ON CONFLICT (worker_id) DO UPDATE SET last_seen = NOW()",
            {"worker_id": worker_id, "hostname": hostname}
        )
        await asyncio.sleep(30)
```

**Cleanup Process**:
```python
# Separate daemon or cron job
async def cleanup_dead_workers():
    # Find stale workers (no heartbeat in 2 minutes)
    stale_workers = await db.execute(
        "SELECT worker_id FROM worker_heartbeats "
        "WHERE last_seen < NOW() - INTERVAL '2 minutes'"
    )

    for worker in stale_workers:
        # Mark jobs as failed
        await db.execute(
            "UPDATE executions SET status = 'failed', "
            "error = 'Worker died unexpectedly' "
            "WHERE worker_id = :worker_id AND status = 'running'",
            {"worker_id": worker.worker_id}
        )

        # Log dead worker
        logger.error(f"Dead worker detected: {worker.worker_id}")
```

**Design Considerations**:
- Heartbeat interval: 30s (balance between overhead and detection time)
- Stale threshold: 2 minutes (3-4 missed heartbeats)
- Cleanup frequency: Every 60 seconds
- Database load: Minimal (one upsert per worker every 30s)

**Why Deferred**:
- Requires new database table and migration
- Needs separate daemon/cron process
- Complex testing (simulating crashes)
- Not critical for MVP (manual monitoring acceptable)
- Can be added post-launch without breaking changes

### References

- [Source: docs/TIER3_PLAN.md - Story NEW-7]
- [Source: docs/architecture.md - Worker reliability]
- [Pattern: Heartbeat](https://martinfowler.com/articles/patterns-of-distributed-systems/heartbeat.html)

## Dev Agent Record

### Context Reference

- Story NOT YET IMPLEMENTED (deferred from Tier 3)

### Future Implementation Notes

**When to implement**:
- After MVP launch
- When manual worker monitoring becomes burdensome
- Before scaling to multiple workers

**Estimated Effort**: 2-3 hours
- 1 hour: Database table, migration, heartbeat logic
- 1 hour: Cleanup daemon, job status updates
- 1 hour: Testing and integration

**Alternative Approaches**:
1. **Process supervisor**: Use systemd/supervisord to restart crashed workers
   - Pro: Simpler, no custom logic
   - Con: Jobs still stuck until restart

2. **External monitoring**: Use Prometheus/Grafana with alerts
   - Pro: Better observability
   - Con: Doesn't auto-recover jobs

3. **Distributed consensus**: Use etcd/Consul for worker registration
   - Pro: More robust
   - Con: Additional infrastructure

**Recommended**: Implement heartbeat approach (as specified) for best balance of simplicity and automation.

### File List

**To be created**:
- database migration for worker_heartbeats table
- worker heartbeat logic in runner/runner/worker.py
- cleanup daemon script (e.g., runner/cleanup_daemon.py)
- integration tests for dead worker detection

**Related Documentation**:
- docs/TIER3_PLAN.md (original story specification)
- docs/TIER3_SUMMARY.md (explains why deferred)
