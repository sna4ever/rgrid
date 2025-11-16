"""
Orchestrator service for RGrid.

The orchestrator is responsible for:
- Worker health monitoring (heartbeats)
- Dead worker detection and cleanup
- Auto-scaling based on queue depth
- Worker provisioning and termination
- Billing hour optimization
"""

__version__ = "0.1.0"
