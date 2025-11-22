#!/bin/bash
# Smoke test script for staging environment
# STAGE-1: Staging Environment Smoke Tests
#
# Usage:
#   ./scripts/smoke-test-staging.sh          # Run all smoke tests
#   ./scripts/smoke-test-staging.sh --quick  # Quick health check only
#
# Exit codes:
#   0 - All tests passed
#   1 - Some tests failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "RGrid Staging Smoke Tests"
echo "=================================="
echo ""

# Quick mode - just health check
if [[ "$1" == "--quick" ]]; then
    echo "Running quick health check..."

    # Test API health
    echo -n "API Health: "
    response=$(curl -s -o /dev/null -w "%{http_code}" https://staging.rgrid.dev/api/v1/health)
    if [[ "$response" == "200" ]]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
    else
        echo -e "${RED}FAIL${NC} (HTTP $response)"
        exit 1
    fi

    # Test database via health
    echo -n "Database:   "
    db_status=$(curl -s https://staging.rgrid.dev/api/v1/health | grep -o '"status":"[^"]*"' | head -1)
    if [[ "$db_status" == *"connected"* ]]; then
        echo -e "${GREEN}PASS${NC} ($db_status)"
    else
        echo -e "${RED}FAIL${NC} ($db_status)"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}Quick health check passed!${NC}"
    exit 0
fi

# Full test suite
echo "Running full smoke test suite..."
echo ""

cd "$PROJECT_ROOT"

# Ensure we're testing staging
export RGRID_TEST_ENV=staging

# Run pytest smoke tests
if venv/bin/pytest tests/smoke/test_deployed_system.py -v --tb=short; then
    echo ""
    echo -e "${GREEN}=================================="
    echo "All smoke tests PASSED!"
    echo "==================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=================================="
    echo "Some smoke tests FAILED!"
    echo "==================================${NC}"
    exit 1
fi
