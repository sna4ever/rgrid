# RGrid – Orchestrator Design (Condensed)

Responsibilities:
- Watch **global queue depth** (total across all projects).
- Decide desired node counts based on total demand.
- Call Hetzner API to create/destroy CX22 nodes.
- Track node states (active, draining, terminated).
- Monitor heartbeats and requeue jobs from dead nodes.
- Enforce timeouts and retry policies.
- Aggregate cost metrics per project/day.

**Architecture:** Global shared pool - nodes are NOT dedicated per project. Any worker can claim jobs from any project, enabling maximum resource utilization and cost efficiency.

Scaling rule (simplified):

```python
total_queued = COUNT(*) FROM jobs WHERE status = 'queued'
desired_nodes = ceil(total_queued / 2)  # 2 concurrent jobs per CX22 node
```

For CX22 with 2 vCPUs and 1 job per vCPU policy, each node handles 2 concurrent jobs from the global queue.
