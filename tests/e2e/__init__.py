"""
End-to-end tests for RGrid CLI commands.

These tests run against the staging environment to verify complete workflows.
They test the CLI commands as a user would invoke them.

Usage:
    # Run all E2E tests
    export RGRID_TEST_ENV=staging
    pytest tests/e2e/ -v

    # Run specific test file
    pytest tests/e2e/test_batch_workflow.py -v

Requirements:
    - Staging environment must be deployed and accessible
    - CLI must be configured with valid API key (rgrid init)
    - Internet connectivity required
"""
