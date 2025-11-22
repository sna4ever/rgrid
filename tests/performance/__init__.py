"""
Performance tests for RGrid API and CLI.

These tests measure response times and throughput against defined SLAs:
- API response time: < 2s
- CLI response time: < 500ms
- Concurrent executions: 100+ simultaneous
- Execution start time: median < 30s

Run with: pytest tests/performance/ -v --performance
"""
