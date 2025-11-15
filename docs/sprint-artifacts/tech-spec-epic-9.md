# Epic Technical Specification: Cost Tracking & Billing

Date: 2025-11-15
Author: BMad
Epic ID: 9
Status: Draft

---

## Overview

Epic 9 implements transparent, predictable cost tracking with per-execution granularity, giving users complete visibility into infrastructure spending. By using the MICRONS pattern (integer micros, 1 EUR = 1,000,000 micros) for exact precision, implementing billing hour amortization to maximize cost efficiency, and providing `rgrid cost` and `rgrid estimate` commands, this epic ensures developers know exactly what they're paying for with no surprise bills.

The implementation focuses on fairness and transparency - costs are amortized across jobs sharing billing hours, estimates are provided before execution, and itemized breakdowns show per-execution costs. This epic delivers on the "no surprise bills" promise while maintaining sub-cent precision through integer arithmetic.

## Objectives and Scope

**In Scope:**
- MICRONS cost pattern (integer arithmetic, 1 EUR = 1,000,000 micros)
- Per-execution cost calculation (duration × hourly worker cost)
- Billing hour cost amortization (share hourly cost across all jobs in same hour)
- `rgrid cost` command (view spending by date range)
- `rgrid estimate` command (predict batch execution cost before running)
- Cost display in status command (Epic 8 integration)
- Cost metadata in database (cost_micros, finalized_cost_micros)
- Worker hourly cost tracking (Hetzner CX22: €5.83/hr = 5,830,000 micros)

**Out of Scope:**
- Payment processing (Stripe integration deferred to post-MVP)
- Account credits system (prepaid credits, post-MVP)
- Cost alerts/limits (e.g., spending >€50/month triggers alert, future enhancement)
- Multi-currency support (EUR only in MVP)
- Tax calculation (future: VAT/GST by region)

## System Architecture Alignment

**Components Involved:**
- **Orchestrator (orchestrator/)**: Cost calculation, billing hour tracking, finalization
- **API (api/)**: Cost query endpoints, estimate calculations
- **CLI (cli/)**: Cost/estimate commands, cost display
- **Database (Postgres)**: Worker costs, execution costs, billing hours

**Architecture Constraints:**
- All costs stored as BIGINT (microns) - no float arithmetic
- Worker hourly cost: €5.83/hr = 5,830,000 micros (Hetzner CX22 prorated)
- Billing hour boundaries tracked per worker (billing_hour_start timestamp)
- Cost finalization happens after billing hour ends (two-phase: estimated → finalized)

**Cross-Epic Dependencies:**
- Requires Epic 4: Worker provisioning, billing hour tracking
- Leverages Epic 8: Cost displayed in status command
- Feeds Epic 10: Cost displayed in web console

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|----------|--------|
| **Cost Calculator** (`orchestrator/cost.py`) | Calculate per-execution cost based on duration | Execution duration, worker cost | Cost in microns | Orchestrator Team |
| **Billing Hour Manager** (`orchestrator/billing.py`) | Track billing hours, finalize costs | Worker billing_hour_start, jobs | Finalized cost per job | Orchestrator Team |
| **Cost Estimator** (`api/services/estimator.py`) | Estimate batch execution cost | Batch size, runtime, historical data | Estimated cost | API Team |
| **CLI Cost Command** (`cli/rgrid/commands/cost.py`) | Display spending by date range | Date range | Cost breakdown table | CLI Team |
| **CLI Estimate Command** (`cli/rgrid/commands/estimate.py`) | Show batch cost estimate | Batch params | Estimated cost display | CLI Team |

### Data Models and Contracts

**Execution Cost (Updates to `executions` table):**
```python
class Execution(Base):
    # ... existing fields from Epic 2/8 ...

    # Epic 9 additions:
    cost_micros: int               # Initial estimated cost (duration × hourly_cost)
    finalized_cost_micros: int     # Final cost after billing hour amortization (null until finalized)
    cost_finalized_at: datetime    # When cost was finalized (null until finalized)

    # Finalized cost is lower if multiple jobs share billing hour
    # Example: 10 jobs in 1 billing hour → €5.83 / 10 = €0.58 per job
```

**Worker Cost Metadata (from Epic 4, used for calculation):**
```python
class Worker(Base):
    # ... existing fields from Epic 4 ...

    hourly_cost_micros: int        # €5.83/hr = 5,830,000 micros (Hetzner CX22)
    billing_hour_start: datetime   # When billing hour started (for amortization)
```

**Cost Response:**
```python
# GET /api/v1/cost?since=2025-11-01&until=2025-11-15
class CostResponse(BaseModel):
    start_date: str                # YYYY-MM-DD
    end_date: str                  # YYYY-MM-DD
    total_cost_micros: int         # Sum of all execution costs
    total_cost_display: str        # "€2.47" (formatted)

    by_date: List[DailyCost]       # Daily breakdown
    total_executions: int          # Count

class DailyCost(BaseModel):
    date: str                      # YYYY-MM-DD
    executions: int                # Count for this day
    compute_time_seconds: int      # Total execution duration
    cost_micros: int               # Total cost for this day
    cost_display: str              # "€0.18"
```

**Estimate Response:**
```python
# GET /api/v1/estimate?runtime=python:3.11&files=100
class EstimateResponse(BaseModel):
    estimated_executions: int      # Number of executions (batch size)
    estimated_duration_seconds: int  # Per-execution average (from historical data)
    estimated_total_duration_seconds: int  # Total compute time
    estimated_cost_micros: int     # Total estimated cost
    estimated_cost_display: str    # "€1.20"

    assumptions: List[str]         # Assumptions made for estimate
    # e.g., ["Based on 50 similar executions with avg duration 30s"]
```

### APIs and Interfaces

**Cost Calculation (MICRONS Pattern):**
```python
# orchestrator/cost.py
def calculate_execution_cost(
    duration_seconds: int,
    hourly_cost_micros: int
) -> int:
    """
    Calculate execution cost in microns (integer arithmetic).

    Formula: cost_micros = (duration_seconds / 3600) * hourly_cost_micros

    Args:
        duration_seconds: Execution runtime (e.g., 120s)
        hourly_cost_micros: Worker hourly cost (e.g., 5,830,000 for CX22)

    Returns:
        Cost in microns (integer)

    Example:
        >>> calculate_execution_cost(120, 5_830_000)
        194333  # €0.194333 (120s of €5.83/hr worker)

    Implementation:
        Use integer arithmetic only (no floats):
        cost_micros = (duration_seconds * hourly_cost_micros) // 3600
    """
    # Integer division (floor division)
    cost_micros = (duration_seconds * hourly_cost_micros) // 3600
    return cost_micros


def format_cost_display(cost_micros: int) -> str:
    """
    Format cost for human-readable display.

    Args:
        cost_micros: Cost in microns

    Returns:
        Formatted string (e.g., "€0.19")

    Example:
        >>> format_cost_display(194333)
        '€0.19'  # Rounded to 2 decimal places
    """
    euros = cost_micros / 1_000_000
    return f"€{euros:.2f}"
```

**Billing Hour Cost Amortization:**
```python
# orchestrator/billing.py
async def finalize_billing_hour_costs(worker_id: str):
    """
    Finalize costs for completed billing hour.

    Called when:
    - Worker terminated after billing hour ends
    - Billing hour ends and worker is idle

    Algorithm:
    1. Find all executions in billing hour (billing_hour_start to billing_hour_start + 1 hour)
    2. Calculate total_jobs_in_hour
    3. Amortize hourly cost: finalized_cost = hourly_cost / total_jobs
    4. Update each execution: finalized_cost_micros, cost_finalized_at

    Args:
        worker_id: Worker ID

    Side effects:
        Updates executions table with finalized costs
    """
    # Get worker billing hour boundaries
    worker = await db.get_worker(worker_id)
    billing_hour_start = worker.billing_hour_start
    billing_hour_end = billing_hour_start + timedelta(hours=1)

    # Find all executions in this billing hour
    executions = await db.query(
        """
        SELECT execution_id, duration_seconds
        FROM executions
        WHERE worker_id = :worker_id
          AND started_at >= :billing_start
          AND started_at < :billing_end
          AND status IN ('completed', 'failed')
        """,
        {
            "worker_id": worker_id,
            "billing_start": billing_hour_start,
            "billing_end": billing_hour_end
        }
    )

    if not executions:
        logger.info(f"No executions in billing hour for {worker_id}, no cost to amortize")
        return

    # Amortize hourly cost across all jobs
    hourly_cost = worker.hourly_cost_micros
    total_jobs = len(executions)
    cost_per_job = hourly_cost // total_jobs  # Integer division

    logger.info(f"Finalizing {total_jobs} jobs for {worker_id}: "
                f"€{hourly_cost/1_000_000:.2f} / {total_jobs} = "
                f"€{cost_per_job/1_000_000:.2f} per job")

    # Update each execution
    for execution in executions:
        await db.execute(
            """
            UPDATE executions
            SET finalized_cost_micros = :finalized_cost,
                cost_finalized_at = NOW()
            WHERE execution_id = :exec_id
            """,
            {
                "exec_id": execution.execution_id,
                "finalized_cost": cost_per_job
            }
        )

    logger.info(f"Finalized costs for billing hour: {worker_id}")
```

**Cost Estimation (Historical Data):**
```python
# api/services/estimator.py
async def estimate_batch_cost(
    runtime: str,
    file_count: int,
    script_content: Optional[str] = None
) -> EstimateResponse:
    """
    Estimate cost for batch execution.

    Strategy:
    1. Query historical executions with same runtime
    2. Calculate average duration (p50)
    3. Estimate: total_duration = file_count × avg_duration
    4. Estimate cost: (total_duration / 3600) × hourly_cost

    Args:
        runtime: Runtime string (e.g., "python:3.11")
        file_count: Number of files in batch
        script_content: Optional script for better estimate (match similar scripts)

    Returns:
        EstimateResponse with cost breakdown
    """
    # Query recent executions (last 30 days)
    historical = await db.query(
        """
        SELECT duration_seconds
        FROM executions
        WHERE runtime = :runtime
          AND status = 'completed'
          AND created_at > NOW() - INTERVAL '30 days'
        ORDER BY created_at DESC
        LIMIT 100
        """,
        {"runtime": runtime}
    )

    if not historical:
        # No historical data: use conservative estimate (60s per execution)
        avg_duration = 60
        assumptions = ["No historical data available, using 60s default estimate"]
    else:
        # Calculate p50 (median) duration
        durations = [row.duration_seconds for row in historical]
        avg_duration = int(percentile(durations, 50))
        assumptions = [f"Based on {len(durations)} similar executions with avg duration {avg_duration}s"]

    # Estimate total cost
    total_duration = file_count * avg_duration
    hourly_cost = 5_830_000  # Hetzner CX22 (TODO: make configurable)
    estimated_cost = (total_duration * hourly_cost) // 3600

    return EstimateResponse(
        estimated_executions=file_count,
        estimated_duration_seconds=avg_duration,
        estimated_total_duration_seconds=total_duration,
        estimated_cost_micros=estimated_cost,
        estimated_cost_display=format_cost_display(estimated_cost),
        assumptions=assumptions
    )
```

**CLI Cost Command:**
```python
# cli/rgrid/commands/cost.py
async def cost_command(since: str = None, until: str = None):
    """
    Display cost breakdown by date.

    Example output:
    Date        Executions  Compute Time   Cost
    2025-11-15  45          2.3h           €0.18
    2025-11-14  120         5.1h           €0.39
    2025-11-13  80          3.2h           €0.25

    Total (last 7 days): €2.47
    """
    # Default: last 7 days
    if not since:
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not until:
        until = datetime.utcnow().strftime("%Y-%m-%d")

    response = await api_client.get_cost(since=since, until=until)

    # Display table
    print("Date        Executions  Compute Time   Cost")
    print("=" * 50)
    for day in response.by_date:
        compute_hours = day.compute_time_seconds / 3600
        print(f"{day.date}  {day.executions:>10}  {compute_hours:>5.1f}h        {day.cost_display}")

    print("=" * 50)
    print(f"Total ({since} to {until}): {response.total_cost_display}")
```

**CLI Estimate Command:**
```python
# cli/rgrid/commands/estimate.py
async def estimate_command(runtime: str, batch: str = None):
    """
    Display cost estimate for batch execution.

    Example output:
    Estimated executions: 500
    Estimated duration: ~30s per execution (based on similar scripts)
    Estimated compute time: 4.2 hours (500 × 30s)
    Estimated cost: ~€1.20

    Note: Actual cost may vary based on execution time.
    """
    # Expand batch pattern
    if batch:
        files = glob.glob(batch)
        file_count = len(files)
    else:
        file_count = 1

    response = await api_client.estimate_cost(runtime=runtime, files=file_count)

    print(f"Estimated executions: {response.estimated_executions}")
    print(f"Estimated duration: ~{response.estimated_duration_seconds}s per execution")
    print(f"Estimated compute time: {response.estimated_total_duration_seconds / 3600:.1f} hours")
    print(f"Estimated cost: ~{response.estimated_cost_display}")
    print()
    print("Assumptions:")
    for assumption in response.assumptions:
        print(f"  - {assumption}")
    print()
    print("Note: Actual cost may vary based on execution time.")
```

### Workflows and Sequencing

**Cost Calculation and Finalization Flow:**
```
1. EXECUTION STARTS:
   a. Worker starts execution at 10:30:15
   b. Execution: started_at=10:30:15
   c. Worker billing_hour_start=10:00:00 (rounded down to hour)

2. EXECUTION COMPLETES:
   a. Worker completes at 10:32:38 (duration: 2m 23s = 143 seconds)
   b. Orchestrator calculates estimated cost:
      cost_micros = (143 * 5_830_000) // 3600 = 231,583 micros = €0.23
   c. Update execution: cost_micros=231583, status=completed

3. BILLING HOUR CONTINUES:
   a. More executions run on same worker (10:00-11:00 billing hour)
   b. Total jobs in hour: 10 executions

4. BILLING HOUR ENDS (11:00):
   a. Orchestrator detects billing hour ended (worker idle or terminated)
   b. Finalize costs for billing hour:
      - Total jobs: 10
      - Hourly cost: 5,830,000 micros
      - Cost per job: 5,830,000 / 10 = 583,000 micros = €0.58
   c. Update all 10 executions:
      finalized_cost_micros=583000, cost_finalized_at=NOW()

5. COST DISPLAY:
   a. User runs: rgrid status exec_abc123
   b. CLI shows:
      - Estimated cost: €0.23 (initial calculation)
      - Finalized cost: €0.58 (after amortization)
      - Savings: -€0.35 (cost increased due to low job count in hour)

      OR if 100 jobs in hour:
      - Estimated cost: €0.23
      - Finalized cost: €0.06 (5,830,000 / 100)
      - Savings: +€0.17 (cost decreased due to high job count)

Result: Fair cost allocation, jobs share billing hour cost
```

**Cost Estimate Flow:**
```
1. USER: rgrid estimate --runtime python:3.11 --batch data/*.csv

2. CLI:
   a. Expand glob: data/*.csv → 500 files
   b. Request estimate from API

3. API ESTIMATOR:
   a. Query historical executions:
      - Runtime: python:3.11
      - Last 30 days
      - Completed successfully
   b. Found: 120 executions
   c. Calculate median duration: 30 seconds (p50)
   d. Estimate total duration: 500 × 30s = 15,000s = 4.2 hours
   e. Estimate cost: (15,000 * 5,830,000) // 3600 = 24,291,666 micros = €24.29

4. API → CLI: EstimateResponse

5. CLI DISPLAY:
   Estimated executions: 500
   Estimated duration: ~30s per execution (based on 120 similar scripts)
   Estimated compute time: 4.2 hours (500 × 30s)
   Estimated cost: ~€24.29

   Assumptions:
     - Based on 120 similar executions with avg duration 30s
     - Assumes no caching (first run)
     - Actual cost may vary ±20%

   Note: Actual cost may vary based on execution time.

6. USER: Decides to proceed or optimize script first
```

**Cost Query Flow:**
```
1. USER: rgrid cost --since 2025-11-01

2. CLI → API: GET /api/v1/cost?since=2025-11-01&until=2025-11-15

3. API:
   a. Query executions table:
      SELECT DATE(created_at) as date,
             COUNT(*) as executions,
             SUM(duration_seconds) as compute_time,
             SUM(COALESCE(finalized_cost_micros, cost_micros)) as cost
      FROM executions
      WHERE created_at >= '2025-11-01'
        AND created_at < '2025-11-15'
      GROUP BY DATE(created_at)
      ORDER BY date DESC

   b. Aggregate by date:
      - 2025-11-15: 45 executions, 8280s (2.3h), 180,000 micros (€0.18)
      - 2025-11-14: 120 executions, 18,360s (5.1h), 390,000 micros (€0.39)
      - ...

4. API → CLI: CostResponse

5. CLI DISPLAY:
   Date        Executions  Compute Time   Cost
   ==================================================
   2025-11-15          45  2.3h           €0.18
   2025-11-14         120  5.1h           €0.39
   2025-11-13          80  3.2h           €0.25
   ...
   ==================================================
   Total (2025-11-01 to 2025-11-15): €2.47

   Total executions: 600
   Total compute time: 28.5 hours
```

## Non-Functional Requirements

### Performance

**Targets:**
- **Cost calculation**: < 1ms (simple integer arithmetic)
- **Cost query latency**: < 200ms (aggregation over 10,000 executions)
- **Estimate latency**: < 500ms (historical query + math)
- **Finalization latency**: < 1s for 100 jobs in billing hour

**Scalability:**
- Support 1M executions in cost query (with date range filtering)
- Estimate based on 1000 historical executions (p50 calculation)

**Source:** Architecture performance targets

### Security

**Cost Data Privacy:**
- Cost data is account-scoped (users only see their own costs)
- No cross-account cost visibility

**Source:** Architecture security decisions

### Reliability/Availability

**Cost Accuracy:**
- Integer arithmetic ensures exact precision (no rounding errors)
- Finalized costs sum to exact hourly cost (no money lost/gained)
- Amortization fairness: all jobs in billing hour share cost equally

**Fault Tolerance:**
- If finalization fails: costs remain as estimated (not finalized, slightly higher)
- Finalization retried on next orchestrator loop

**Source:** Architecture reliability patterns

### Observability

**Metrics:**
- Total cost per day/week/month
- Average cost per execution
- Billing hour utilization (jobs per hour)
- Estimate accuracy (estimated vs. actual cost)

**Logging:**
- Orchestrator: Cost finalization events, amortization calculations
- API: Cost query performance, estimate calculations

**Source:** Architecture observability requirements

## Dependencies and Integrations

**Database Schema Updates:**
```sql
-- Updates to executions table
ALTER TABLE executions ADD COLUMN cost_micros BIGINT DEFAULT 0;
ALTER TABLE executions ADD COLUMN finalized_cost_micros BIGINT;
ALTER TABLE executions ADD COLUMN cost_finalized_at TIMESTAMP;

-- Index for cost queries
CREATE INDEX idx_executions_cost_date ON executions(created_at, cost_micros);
CREATE INDEX idx_executions_finalized_cost ON executions(cost_finalized_at);
```

**API Endpoints (New):**
```
GET  /api/v1/cost?since={date}&until={date}    # Cost breakdown by date
GET  /api/v1/estimate?runtime={runtime}&files={count}  # Estimate batch cost
```

## Acceptance Criteria (Authoritative)

**AC-9.1: MICRONS Cost Calculation**
1. Execution costs stored as BIGINT (microns, 1 EUR = 1,000,000 micros)
2. Cost calculated as: (duration_seconds × hourly_cost_micros) // 3600
3. Displayed to user as EUR with 2 decimal places (e.g., "€0.02")

**AC-9.2: Billing Hour Cost Amortization**
1. When billing hour ends, orchestrator calculates jobs in hour
2. Hourly cost divided by job count: cost_per_job = hourly_cost / job_count
3. Each execution updated with finalized_cost_micros

**AC-9.3: rgrid cost Command**
1. When I run `rgrid cost`, CLI displays spending by date (last 7 days default)
2. Output shows: date, executions, compute time, cost per day
3. Total cost displayed at bottom

**AC-9.4: rgrid estimate Command**
1. When I run `rgrid estimate --batch data/*.csv`, CLI shows estimated cost
2. Estimate based on historical data (median duration of similar executions)
3. Output shows: file count, estimated duration, estimated cost

**AC-9.5: Cost Alerts (Future Enhancement)**
1. (Deferred to post-MVP) Users can set spending limits and receive alerts

## Traceability Mapping

| AC | Spec Section | Components/APIs | Test Idea |
|----|--------------|-----------------|-----------|
| AC-9.1 | Cost Calculator | orchestrator/cost.py | Complete execution, verify cost_micros calculated correctly |
| AC-9.2 | Billing Hour Manager | orchestrator/billing.py | Run 10 jobs in 1 hour, verify finalized costs sum to hourly_cost |
| AC-9.3 | CLI: Cost Command | cli/commands/cost.py | Run executions, call cost command, verify breakdown |
| AC-9.4 | Cost Estimator | api/services/estimator.py | Call estimate with batch, verify calculation |
| AC-9.5 | N/A | (Deferred) | N/A |

## Risks, Assumptions, Open Questions

**Risks:**
1. **R1**: Estimate accuracy depends on historical data (new users have no history)
   - **Mitigation**: Use conservative default (60s per execution) if no history
2. **R2**: Worker cost changes (Hetzner price increase)
   - **Mitigation**: Make hourly_cost_micros configurable (environment variable)

**Assumptions:**
1. **A1**: Hetzner CX22 hourly cost stable at €5.83/hr (check quarterly)
2. **A2**: Users accept estimated costs (finalized after billing hour)
3. **A3**: 30-day historical window sufficient for estimates

**Open Questions:**
1. **Q1**: Should we support cost alerts/limits?
   - **Decision**: Yes, but deferred to post-MVP (Story 9.5 marked optional)
2. **Q2**: Should cost include storage costs (MinIO)?
   - **Decision**: No in MVP (compute costs only), storage costs negligible (<€0.01/GB/month)

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**
   - Cost calculation: Test MICRONS arithmetic, verify no rounding errors
   - Amortization: Test division (10 jobs, 100 jobs), verify sum equals hourly cost
   - Estimate: Mock historical data, verify calculation

2. **Integration Tests**
   - Cost finalization: Complete billing hour, verify all jobs finalized
   - Cost query: Query by date range, verify aggregation
   - Estimate: Real historical data, verify reasonable estimate

3. **End-to-End Tests**
   - Complete flow: Run execution → verify cost → verify finalized cost
   - Cost command: Run multiple executions → call cost → verify breakdown
   - Estimate: Call estimate → verify output format

**Frameworks:**
- **Cost math**: Standard Python unittest for arithmetic
- **Database**: pytest-postgresql for aggregation queries

**Coverage of ACs:**
- AC-9.1: Unit test (cost calculation, verify microns precision)
- AC-9.2: Integration test (billing hour amortization, verify fairness)
- AC-9.3: E2E test (run executions, call cost, check output)
- AC-9.4: Integration test (call estimate, verify calculation)
- AC-9.5: (Deferred, no tests in MVP)

**Edge Cases:**
- Execution duration = 0 seconds (cost = 0)
- Execution duration = 1 hour (cost = hourly_cost)
- Billing hour with 1 job (full hourly cost to that job)
- Billing hour with 1000 jobs (cost per job = hourly_cost / 1000)
- No historical data for estimate (use default 60s)

**Performance Tests:**
- Cost query: 100,000 executions, measure aggregation time
- Estimate query: 1000 historical executions, measure p50 calculation

---

**Epic Status**: Ready for Story Implementation
**Next Action**: Run `create-story` workflow to draft Story 9.1
