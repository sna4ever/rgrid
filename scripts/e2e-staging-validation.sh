#!/bin/bash
# STAGE-2: End-to-End Workflow Validation Script
#
# This script runs the comprehensive E2E workflow tests against staging.
#
# Usage:
#   # With staging API key set
#   export STAGING_API_KEY=<your-test-key>
#   ./scripts/e2e-staging-validation.sh
#
#   # Quick validation (skip slow tests)
#   ./scripts/e2e-staging-validation.sh --quick
#
#   # With verbose output
#   ./scripts/e2e-staging-validation.sh -v
#
# Exit codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Configuration error (no API key)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "======================================"
echo "STAGE-2: E2E Workflow Validation"
echo "======================================"
echo ""

# Check for API key
if [[ -z "${STAGING_API_KEY}" ]]; then
    echo -e "${YELLOW}Warning: STAGING_API_KEY not set${NC}"
    echo "Tests will be skipped unless you set the staging API key."
    echo ""
    echo "To run actual staging tests:"
    echo "  export STAGING_API_KEY=<your-staging-api-key>"
    echo ""
    echo -e "${CYAN}Running tests (will skip staging-required tests)...${NC}"
    echo ""
fi

# Parse arguments
VERBOSE=""
QUICK=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE="-v" ;;
        --quick) QUICK="-m 'not slow'" ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose    Show verbose test output"
            echo "  --quick          Skip slow tests (> 30s)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

cd "$PROJECT_ROOT"

# Ensure staging URL is set
export STAGING_API_URL="${STAGING_API_URL:-https://staging.rgrid.dev}"

echo "Staging URL: $STAGING_API_URL"
echo "API Key: ${STAGING_API_KEY:+***configured***}${STAGING_API_KEY:-NOT SET}"
echo ""

# Run the E2E staging workflow tests
echo "Running E2E workflow validation tests..."
echo ""

if [[ -n "$QUICK" ]]; then
    # Quick mode - skip slow tests
    venv/bin/pytest tests/e2e/test_staging_workflow.py $VERBOSE --tb=short -m "not slow" 2>&1 || TEST_EXIT=$?
else
    # Full test suite
    venv/bin/pytest tests/e2e/test_staging_workflow.py $VERBOSE --tb=short 2>&1 || TEST_EXIT=$?
fi

# Report results
echo ""
if [[ ${TEST_EXIT:-0} -eq 0 ]]; then
    echo -e "${GREEN}======================================"
    echo "E2E Workflow Validation: PASSED"
    echo "======================================${NC}"
    exit 0
else
    echo -e "${RED}======================================"
    echo "E2E Workflow Validation: FAILED"
    echo "======================================${NC}"
    echo ""
    echo "Some tests failed. Check output above for details."
    exit 1
fi
