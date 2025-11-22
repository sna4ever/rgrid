"""
Shared fixtures for E2E tests.

These fixtures provide:
- Staging API URL configuration
- Click test runner setup
- Temporary test files and directories
- Test execution cleanup
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Default to staging environment
STAGING_API_URL = os.getenv('STAGING_API_URL', 'https://staging.rgrid.dev/api/v1')


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def staging_api_url():
    """Return staging API URL."""
    return STAGING_API_URL


@pytest.fixture
def temp_script_dir():
    """Create temporary directory with test scripts."""
    temp_dir = tempfile.mkdtemp(prefix="rgrid_e2e_")
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def simple_script(temp_script_dir):
    """Create a simple Python script for testing."""
    script_path = Path(temp_script_dir) / "simple.py"
    script_path.write_text("""
import sys
print("Hello from RGrid E2E test!")
print(f"Args: {sys.argv[1:]}")
""")
    return str(script_path)


@pytest.fixture
def output_script(temp_script_dir):
    """Create a Python script that produces output files."""
    script_path = Path(temp_script_dir) / "output_script.py"
    script_path.write_text("""
import sys
import json

# Read input if provided
input_data = None
if len(sys.argv) > 1:
    try:
        with open(sys.argv[1]) as f:
            input_data = f.read()
    except:
        input_data = sys.argv[1]

# Write output
with open('output.json', 'w') as f:
    json.dump({'processed': True, 'input': input_data}, f)

print(f"Processed: {input_data}")
""")
    return str(script_path)


@pytest.fixture
def batch_test_files(temp_script_dir):
    """Create multiple test files for batch processing."""
    files = []
    for i in range(3):
        file_path = Path(temp_script_dir) / f"test_{i}.txt"
        file_path.write_text(f"Test data {i}")
        files.append(str(file_path))
    return files


@pytest.fixture
def mock_api_client():
    """Create mock API client for unit-style E2E tests."""
    mock_client = MagicMock()

    # Default return values for common operations
    mock_client.create_execution.return_value = {
        "execution_id": "exec_test123",
        "status": "queued",
        "upload_urls": {},
    }
    mock_client.get_execution.return_value = {
        "execution_id": "exec_test123",
        "status": "completed",
        "runtime": "python:3.11",
        "exit_code": 0,
        "stdout": "Hello from test!",
        "stderr": "",
        "created_at": "2025-11-22T10:00:00Z",
        "started_at": "2025-11-22T10:00:05Z",
        "completed_at": "2025-11-22T10:00:10Z",
    }
    mock_client.get_cost.return_value = {
        "start_date": "2025-11-15",
        "end_date": "2025-11-22",
        "by_date": [
            {
                "date": "2025-11-22",
                "executions": 5,
                "compute_time_seconds": 120,
                "cost_display": "$0.002",
            }
        ],
        "total_executions": 5,
        "total_cost_display": "$0.002",
    }
    mock_client.get_artifacts.return_value = [
        {
            "filename": "output.json",
            "artifact_type": "output",
            "size_bytes": 256,
            "file_path": "artifacts/exec_test123/output.json",
        }
    ]

    return mock_client


@pytest.fixture
def mock_credentials(staging_api_url):
    """Mock credentials for CLI commands."""
    return {
        "api_url": staging_api_url,
        "api_key": "test_api_key_e2e",
    }


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (may take >30s)"
    )
    config.addinivalue_line(
        "markers", "requires_staging: test requires staging environment"
    )
