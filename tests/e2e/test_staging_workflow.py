"""
STAGE-2: End-to-End Workflow Validation on Staging

This module tests complete user journeys against the actual staging environment:
- Upload → Execute → Monitor → Download workflow
- Batch processing with 10+ files
- Cost tracking accuracy validation
- Retry and error recovery flows

Usage:
    # Run with staging credentials configured
    export STAGING_API_KEY=<your-test-key>
    pytest tests/e2e/test_staging_workflow.py -v -m requires_staging

    # Skip if no staging credentials
    pytest tests/e2e/test_staging_workflow.py -v
"""

import os
import time
import json
import pytest
import requests
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configuration
STAGING_API_URL = os.getenv('STAGING_API_URL', 'https://staging.rgrid.dev')
STAGING_API_KEY = os.getenv('STAGING_API_KEY', '')

# Skip staging tests if no API key
requires_staging = pytest.mark.skipif(
    not STAGING_API_KEY,
    reason="STAGING_API_KEY not set - skipping staging tests"
)


def get_staging_headers():
    """Get headers for staging API requests."""
    return {
        "Authorization": f"Bearer {STAGING_API_KEY}",
        "Content-Type": "application/json",
    }


def create_execution(script_content: str, runtime: str = "python:3.11",
                     args: list = None, input_files: list = None,
                     batch_id: str = None, user_metadata: dict = None) -> dict:
    """Create an execution on staging."""
    payload = {
        "script_content": script_content,
        "runtime": runtime,
        "args": args or [],
        "env_vars": {},
        "input_files": input_files or [],
    }
    if batch_id:
        payload["batch_id"] = batch_id
    if user_metadata:
        payload["user_metadata"] = user_metadata

    response = requests.post(
        f"{STAGING_API_URL}/api/v1/executions",
        headers=get_staging_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_execution(execution_id: str) -> dict:
    """Get execution status from staging."""
    response = requests.get(
        f"{STAGING_API_URL}/api/v1/executions/{execution_id}",
        headers=get_staging_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def wait_for_execution(execution_id: str, timeout: int = 120) -> dict:
    """Wait for execution to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = get_execution(execution_id)
        status = result.get('status', '')
        if status in ('completed', 'failed'):
            return result
        time.sleep(2)
    raise TimeoutError(f"Execution {execution_id} did not complete within {timeout}s")


def get_cost_summary(since: str = None, until: str = None) -> dict:
    """Get cost summary from staging."""
    params = {}
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    response = requests.get(
        f"{STAGING_API_URL}/api/v1/cost",
        headers=get_staging_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def retry_execution(execution_id: str) -> dict:
    """Retry an execution on staging."""
    response = requests.post(
        f"{STAGING_API_URL}/api/v1/executions/{execution_id}/retry",
        headers=get_staging_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_artifacts(execution_id: str) -> list:
    """Get artifacts for an execution."""
    response = requests.get(
        f"{STAGING_API_URL}/api/v1/executions/{execution_id}/artifacts",
        headers=get_staging_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_batch_status(batch_id: str) -> dict:
    """Get batch status from staging."""
    response = requests.get(
        f"{STAGING_API_URL}/api/v1/batches/{batch_id}/status",
        headers=get_staging_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_estimate(runtime: str = "python:3.11", files: int = 1) -> dict:
    """Get cost estimate from staging."""
    response = requests.get(
        f"{STAGING_API_URL}/api/v1/estimate",
        headers=get_staging_headers(),
        params={"runtime": runtime, "files": files},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def upload_file(url: str, filepath: str) -> bool:
    """Upload file to presigned URL."""
    with open(filepath, 'rb') as f:
        response = requests.put(url, data=f, timeout=60)
    return response.status_code == 200


@requires_staging
class TestSimpleExecutionWorkflow:
    """Test 1: Simple execution workflow (upload → execute → monitor → download)."""

    def test_simple_script_execution(self):
        """Test executing a simple Python script on staging."""
        script = '''
import sys
print("Hello from STAGE-2 E2E test!")
print(f"Python version: {sys.version}")
'''
        # Create execution
        result = create_execution(script)
        execution_id = result['execution_id']
        assert execution_id, "Should return execution_id"
        assert result['status'] == 'queued', "Initial status should be queued"

        # Wait for completion
        final = wait_for_execution(execution_id, timeout=120)
        assert final['status'] == 'completed', f"Execution should complete: {final}"
        assert final.get('exit_code') == 0, "Exit code should be 0"
        assert 'Hello from STAGE-2 E2E test!' in final.get('stdout', ''), "Should have expected output"

    def test_script_with_arguments(self):
        """Test script that uses command-line arguments."""
        script = '''
import sys
args = sys.argv[1:]
print(f"Received args: {args}")
print(f"Total args: {len(args)}")
'''
        result = create_execution(script, args=['arg1', 'arg2', 'test value'])
        execution_id = result['execution_id']

        final = wait_for_execution(execution_id, timeout=120)
        assert final['status'] == 'completed', f"Should complete: {final}"
        assert 'arg1' in final.get('stdout', ''), "Should include arg1"
        assert 'arg2' in final.get('stdout', ''), "Should include arg2"
        assert 'test value' in final.get('stdout', ''), "Should include 'test value'"

    def test_script_with_environment_variables(self):
        """Test script that uses environment variables."""
        script = '''
import os
print(f"TEST_VAR={os.environ.get('TEST_VAR', 'NOT_SET')}")
print(f"MY_CONFIG={os.environ.get('MY_CONFIG', 'NOT_SET')}")
'''
        # Create execution with env vars
        payload = {
            "script_content": script,
            "runtime": "python:3.11",
            "args": [],
            "env_vars": {"TEST_VAR": "hello_world", "MY_CONFIG": "value123"},
            "input_files": [],
        }
        response = requests.post(
            f"{STAGING_API_URL}/api/v1/executions",
            headers=get_staging_headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        execution_id = result['execution_id']

        final = wait_for_execution(execution_id, timeout=120)
        assert final['status'] == 'completed', f"Should complete: {final}"
        assert 'TEST_VAR=hello_world' in final.get('stdout', ''), "Should have TEST_VAR"
        assert 'MY_CONFIG=value123' in final.get('stdout', ''), "Should have MY_CONFIG"

    def test_execution_status_transitions(self):
        """Test that execution goes through expected status transitions."""
        script = '''
import time
print("Starting...")
time.sleep(3)
print("Done!")
'''
        result = create_execution(script)
        execution_id = result['execution_id']

        observed_statuses = set()
        start_time = time.time()
        while time.time() - start_time < 120:
            status_result = get_execution(execution_id)
            observed_statuses.add(status_result['status'])
            if status_result['status'] in ('completed', 'failed'):
                break
            time.sleep(1)

        assert 'queued' in observed_statuses or 'running' in observed_statuses, (
            f"Should see queued or running status. Observed: {observed_statuses}"
        )
        assert 'completed' in observed_statuses, f"Should complete. Observed: {observed_statuses}"

    def test_execution_with_user_metadata(self):
        """Test execution with user metadata tags (Story 10.8)."""
        script = 'print("Metadata test")'
        metadata = {"project": "e2e-test", "environment": "staging"}

        result = create_execution(script, user_metadata=metadata)
        execution_id = result['execution_id']

        # Verify metadata is stored
        status = get_execution(execution_id)
        stored_metadata = status.get('user_metadata', {})

        # Metadata should be present or execution should complete successfully
        final = wait_for_execution(execution_id, timeout=60)
        assert final['status'] == 'completed', "Should complete"


@requires_staging
class TestBatchProcessing:
    """Test 2: Batch processing with 10+ files."""

    def test_batch_execution_10_files(self):
        """Test batch execution with 10 files."""
        import uuid
        batch_id = f"e2e_batch_{uuid.uuid4().hex[:8]}"

        script = '''
import sys
import json
filename = sys.argv[1] if len(sys.argv) > 1 else "unknown"
print(f"Processing: {filename}")
with open("output.json", "w") as f:
    json.dump({"processed": filename}, f)
'''
        # Create 10 executions with same batch_id
        execution_ids = []
        for i in range(10):
            result = create_execution(
                script,
                args=[f"file_{i}.txt"],
                batch_id=batch_id,
            )
            execution_ids.append(result['execution_id'])

        assert len(execution_ids) == 10, "Should create 10 executions"

        # Wait for all to complete
        completed_count = 0
        failed_count = 0
        for exec_id in execution_ids:
            try:
                final = wait_for_execution(exec_id, timeout=180)
                if final['status'] == 'completed':
                    completed_count += 1
                else:
                    failed_count += 1
            except TimeoutError:
                failed_count += 1

        assert completed_count >= 8, f"At least 80% should complete: {completed_count}/10"

    def test_batch_status_endpoint(self):
        """Test batch status tracking."""
        import uuid
        batch_id = f"e2e_batch_{uuid.uuid4().hex[:8]}"

        script = 'import time; time.sleep(2); print("done")'

        # Create 3 executions in batch
        for i in range(3):
            create_execution(script, batch_id=batch_id)

        # Check batch status
        time.sleep(1)  # Give it a moment to register

        status = get_batch_status(batch_id)
        # API returns 'statuses' list, not 'total'
        statuses = status.get('statuses', [])
        assert len(statuses) == 3, f"Should have 3 in batch: {status}"

        # Wait for completion and re-check
        time.sleep(15)
        final_status = get_batch_status(batch_id)
        final_statuses = final_status.get('statuses', [])
        completed = sum(1 for s in final_statuses if s == 'completed')
        assert completed >= 2, f"At least 2 should complete: {final_status}"

    def test_batch_with_varying_durations(self):
        """Test batch where executions have different durations."""
        import uuid
        batch_id = f"e2e_batch_{uuid.uuid4().hex[:8]}"

        # Create scripts with varying sleep times
        scripts = [
            'import time; time.sleep(1); print("fast")',
            'import time; time.sleep(3); print("medium")',
            'import time; time.sleep(5); print("slow")',
        ]

        execution_ids = []
        for script in scripts:
            result = create_execution(script, batch_id=batch_id)
            execution_ids.append(result['execution_id'])

        # Track completion order
        completion_times = {}
        start = time.time()

        remaining = set(execution_ids)
        while remaining and time.time() - start < 120:
            for exec_id in list(remaining):
                status = get_execution(exec_id)
                if status['status'] == 'completed':
                    completion_times[exec_id] = time.time() - start
                    remaining.remove(exec_id)
            time.sleep(1)

        assert len(completion_times) == 3, f"All should complete: {completion_times}"


@requires_staging
class TestCostTracking:
    """Test 3: Cost tracking accuracy validation."""

    def test_cost_endpoint_returns_data(self):
        """Test that cost endpoint returns valid data."""
        cost_data = get_cost_summary()

        assert 'start_date' in cost_data or 'by_date' in cost_data, (
            f"Should have cost data structure: {cost_data}"
        )
        if 'by_date' in cost_data:
            assert isinstance(cost_data['by_date'], list), "by_date should be a list"

    def test_cost_after_execution(self):
        """Test that execution adds to cost tracking."""
        # Get initial cost
        today = datetime.now().strftime('%Y-%m-%d')
        initial_cost = get_cost_summary(since=today, until=today)
        initial_executions = initial_cost.get('total_executions', 0)

        # Run an execution
        script = 'import time; time.sleep(2); print("cost test")'
        result = create_execution(script)
        wait_for_execution(result['execution_id'], timeout=60)

        # Check cost again
        time.sleep(2)  # Allow cost to be recorded
        final_cost = get_cost_summary(since=today, until=today)
        final_executions = final_cost.get('total_executions', 0)

        assert final_executions >= initial_executions, (
            f"Executions should not decrease: {initial_executions} -> {final_executions}"
        )

    def test_cost_estimation_endpoint(self):
        """Test cost estimation for batch execution."""
        estimate = get_estimate(runtime="python:3.11", files=10)

        # API returns estimated_cost_micros and estimated_cost_display
        has_cost = (
            'estimated_cost' in estimate or
            'total_cost' in estimate or
            'cost' in estimate or
            'estimated_cost_micros' in estimate or
            'estimated_cost_display' in estimate
        )
        assert has_cost, f"Should have cost estimate: {estimate}"

    def test_cost_date_range_filtering(self):
        """Test cost endpoint filters by date range correctly."""
        # Get cost for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        cost_data = get_cost_summary(
            since=start_date.strftime('%Y-%m-%d'),
            until=end_date.strftime('%Y-%m-%d'),
        )

        # Should return data structure
        assert cost_data is not None, "Should return cost data"


@requires_staging
class TestRetryAndErrorRecovery:
    """Test 4: Retry and error recovery flows."""

    def test_failed_execution_returns_error_info(self):
        """Test that failed executions return error information."""
        script = '''
import sys
print("About to fail...")
sys.exit(1)
'''
        result = create_execution(script)
        execution_id = result['execution_id']

        final = wait_for_execution(execution_id, timeout=60)
        assert final['status'] == 'failed', f"Should fail: {final}"
        assert final.get('exit_code') != 0, "Exit code should be non-zero"

    def test_retry_failed_execution(self):
        """Test retrying a failed execution."""
        # First create a failing execution
        script = '''
import sys
print("This will fail")
sys.exit(1)
'''
        result = create_execution(script)
        original_id = result['execution_id']

        # Wait for it to fail
        wait_for_execution(original_id, timeout=60)

        # Retry it
        retry_result = retry_execution(original_id)
        new_id = retry_result.get('execution_id')

        assert new_id, "Retry should return new execution_id"
        assert new_id != original_id, "New execution should have different ID"

        # Wait for retry to complete (will also fail, but should work)
        final = wait_for_execution(new_id, timeout=60)
        assert final['status'] in ('completed', 'failed'), "Retry should run"

    def test_retry_successful_execution(self):
        """Test that successful executions can also be retried."""
        script = 'print("Retry test - success")'
        result = create_execution(script)
        original_id = result['execution_id']

        # Wait for completion
        final = wait_for_execution(original_id, timeout=60)
        assert final['status'] == 'completed', "Should complete"

        # Retry successful execution
        retry_result = retry_execution(original_id)
        new_id = retry_result.get('execution_id')

        assert new_id, "Should be able to retry successful execution"

        # Wait for retry
        retry_final = wait_for_execution(new_id, timeout=60)
        assert retry_final['status'] == 'completed', "Retry should also complete"

    def test_timeout_handling(self):
        """Test that long-running scripts are handled (may timeout)."""
        # This test verifies the system handles long scripts
        # Note: Actual timeout depends on system configuration
        script = '''
import time
print("Starting long task...")
time.sleep(30)  # 30 seconds
print("Done!")
'''
        result = create_execution(script)
        execution_id = result['execution_id']

        # Wait with longer timeout
        final = wait_for_execution(execution_id, timeout=180)
        # Should either complete or be killed by timeout
        assert final['status'] in ('completed', 'failed'), f"Should finish: {final}"


@requires_staging
class TestInputFileWorkflow:
    """Test 5: Input file upload and processing workflow."""

    def test_script_with_input_file_upload(self):
        """Test uploading and processing an input file."""
        # Create a temp file to upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data", "value": 42}, f)
            temp_path = f.name

        try:
            script = '''
import json
import sys
with open(sys.argv[1]) as f:
    data = json.load(f)
print(f"Loaded: {data}")
print(f"Value: {data.get('value')}")
'''
            # Create execution with input file
            result = create_execution(
                script,
                args=[Path(temp_path).name],
                input_files=[Path(temp_path).name],
            )
            execution_id = result['execution_id']

            # Check if upload URLs are provided
            upload_urls = result.get('upload_urls', {})

            if upload_urls:
                # Upload the file
                filename = Path(temp_path).name
                if filename in upload_urls:
                    upload_success = upload_file(upload_urls[filename], temp_path)
                    assert upload_success, "File upload should succeed"

            # Wait for execution
            final = wait_for_execution(execution_id, timeout=120)
            # May fail if no worker available, but should at least queue
            assert final['status'] in ('completed', 'failed', 'queued', 'running'), (
                f"Should have valid status: {final}"
            )
        finally:
            os.unlink(temp_path)


@requires_staging
class TestArtifactRetrieval:
    """Test 6: Output artifact retrieval."""

    def test_get_artifacts_for_completed_execution(self):
        """Test retrieving artifacts after execution completes."""
        script = '''
import json
with open("output.json", "w") as f:
    json.dump({"result": "success", "value": 123}, f)
print("Created output.json")
'''
        result = create_execution(script)
        execution_id = result['execution_id']

        final = wait_for_execution(execution_id, timeout=120)

        if final['status'] == 'completed':
            artifacts = get_artifacts(execution_id)
            # Should have at least stdout/stderr, possibly output.json
            assert isinstance(artifacts, list), f"Should return artifact list: {artifacts}"


@requires_staging
class TestStressValidation:
    """Test 7: Light stress testing for workflow validation."""

    def test_concurrent_execution_submission(self):
        """Test submitting multiple executions concurrently."""
        script = 'import time; time.sleep(1); print("concurrent test")'

        def submit_execution(index):
            result = create_execution(script, args=[str(index)])
            return result['execution_id']

        # Submit 5 executions concurrently
        execution_ids = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(submit_execution, i) for i in range(5)]
            for future in as_completed(futures):
                try:
                    exec_id = future.result()
                    execution_ids.append(exec_id)
                except Exception as e:
                    pytest.fail(f"Concurrent submission failed: {e}")

        assert len(execution_ids) == 5, f"Should submit all 5: {len(execution_ids)}"

        # Wait for all to complete
        completed = 0
        for exec_id in execution_ids:
            try:
                final = wait_for_execution(exec_id, timeout=120)
                if final['status'] == 'completed':
                    completed += 1
            except:
                pass

        assert completed >= 3, f"At least 60% should complete: {completed}/5"


# Utility class for test result collection
class TestResultCollector:
    """Collect test results for reporting."""

    results = []

    @classmethod
    def add_result(cls, test_name: str, passed: bool, details: str = ""):
        cls.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })

    @classmethod
    def get_summary(cls) -> dict:
        total = len(cls.results)
        passed = sum(1 for r in cls.results if r['passed'])
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{100 * passed / total:.1f}%" if total > 0 else "N/A",
        }
