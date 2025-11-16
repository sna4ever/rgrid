# Error Reference

This document lists all structured error types in RGrid, their meanings, and how to resolve them.

RGrid uses structured errors to provide clear, actionable guidance when things go wrong. Each error includes:
- **Error Type**: Categorizes the kind of problem
- **Message**: Human-readable description of what went wrong
- **Context**: Relevant details (file paths, IDs, timestamps, etc.)
- **Suggestions**: Actionable steps to resolve the issue

## Error Hierarchy

All RGrid errors inherit from `RGridError`:

```
RGridError (base class)
├── ValidationError
├── ExecutionError
├── TimeoutError
├── NetworkError
├── AuthenticationError
├── ResourceNotFoundError
└── QuotaExceededError
```

---

## ValidationError

**Category**: User Input Validation

**When It Occurs**: User-provided input is invalid, missing, or malformed.

**HTTP Status Code**: 400 Bad Request

### Common Scenarios

#### Script File Not Found

```
❌ Validation Error: Script file not found

   Context:
   - file: nonexistent.py
   - location: /home/user/projects

💡 Suggestions:
   - Check the file path is correct
   - Ensure the file exists in the current directory
   - Use absolute path if the file is elsewhere
```

**Cause**: The script file specified does not exist at the given path.

**Resolution**:
1. Verify the file path is spelled correctly
2. Check the file exists: `ls -la <filename>`
3. Use an absolute path if the file is in a different directory
4. Ensure you're in the correct working directory

---

#### Invalid Runtime

```
❌ Validation Error: Invalid runtime: ruby3.0

   Context:
   - requested: ruby3.0
   - available: python3.11, python3.12, node20, node22

💡 Suggestions:
   - Check the input parameters are correct
   - Refer to documentation for valid values
```

**Cause**: The specified runtime is not supported.

**Resolution**:
1. Use one of the available runtimes listed in the error
2. Check documentation for supported runtimes: `rgrid runtimes --list`
3. Omit `--runtime` to use the default (python3.11)

---

#### Invalid Environment Variable Format

```
❌ Validation Error: Invalid environment variable format

   Context:
   - provided: API_KEYmysecret
   - expected_format: KEY=VALUE
   - example: API_KEY=my_secret_key

💡 Suggestions:
   - Check the input parameters are correct
   - Refer to documentation for valid values
```

**Cause**: Environment variable not in `KEY=VALUE` format.

**Resolution**:
1. Use the format: `--env KEY=VALUE`
2. Example: `rgrid run script.py --env API_KEY=abc123 --env DEBUG=true`
3. Ensure there's an `=` sign between the key and value

---

## ExecutionError

**Category**: Script Execution Failure

**When It Occurs**: A script fails during execution on the runner.

**HTTP Status Code**: 500 Internal Server Error

### Common Scenarios

#### Non-Zero Exit Code

```
❌ Execution Error: Script exited with non-zero status

   Context:
   - exec_id: exec-abc123
   - exit_code: 1
   - script: process.py

💡 Suggestions:
   - Check script logs for details
   - Verify script runs locally first
   - Ensure all dependencies are included
   - Check resource limits (memory, CPU)
```

**Cause**: The script terminated with a non-zero exit code, indicating an error.

**Resolution**:
1. View the logs: `rgrid logs <exec_id>`
2. Run the script locally to reproduce the error
3. Check for missing dependencies in `requirements.txt`
4. Verify the script has proper error handling

---

#### Container Failed to Start

```
❌ Execution Error: Container failed to start

   Context:
   - exec_id: exec-abc123
   - runtime: python:3.11
   - error: image not found

💡 Suggestions:
   - Check script logs for details
   - Verify script runs locally first
   - Ensure all dependencies are included
```

**Cause**: The Docker container could not be started (usually invalid runtime or resource limits).

**Resolution**:
1. Verify the runtime is valid
2. Check resource limits are reasonable
3. Contact support if the issue persists

---

## TimeoutError

**Category**: Job Timeout

**When It Occurs**: A job exceeds its configured timeout.

**HTTP Status Code**: 408 Request Timeout

### Example

```
❌ Timeout Error: Execution timed out after 60 seconds

   Context:
   - exec_id: exec-xyz789
   - timeout: 60
   - elapsed: 61

💡 Suggestions:
   - Increase timeout with --timeout flag
   - Optimize script to run faster
   - Break large jobs into smaller chunks
   - Check for infinite loops or hangs
```

**Cause**: The script ran longer than the configured timeout.

**Resolution**:
1. Increase timeout: `rgrid run script.py --timeout 300` (5 minutes)
2. Optimize your script to run faster
3. Break large processing jobs into smaller batches
4. Check for infinite loops or blocking I/O operations
5. Default timeout is 300 seconds (5 minutes)

---

## NetworkError

**Category**: API/Network Communication

**When It Occurs**: API calls fail due to network issues.

**HTTP Status Code**: 503 Service Unavailable

### Common Scenarios

#### Connection Refused

```
❌ Network Error: Failed to connect to API

   Context:
   - endpoint: https://api.rgrid.io/v1/jobs
   - error: Connection refused

💡 Suggestions:
   - Check network connection
   - Verify API endpoint is reachable
   - Check API status page for outages
   - Retry the request after a brief delay
```

**Cause**: Cannot connect to the RGrid API.

**Resolution**:
1. Check your internet connection
2. Verify the API endpoint is correct
3. Check firewall/proxy settings
4. Visit status page for API outages
5. Retry after a few moments

---

#### API Unreachable

```
❌ Network Error: API endpoint unreachable

   Context:
   - endpoint: https://api.rgrid.io/v1/executions
   - status_code: 503

💡 Suggestions:
   - Check network connection
   - Verify API endpoint is reachable
   - Check API status page for outages
```

**Cause**: API returned 503 Service Unavailable.

**Resolution**:
1. Check API status page for maintenance/outages
2. Retry after a brief delay
3. Contact support if the issue persists

---

## AuthenticationError

**Category**: Authentication/Authorization

**When It Occurs**: Authentication fails or user lacks permissions.

**HTTP Status Code**: 401 Unauthorized

### Example

```
❌ Authentication Error: Invalid or expired API token

   Context:
   - endpoint: /v1/jobs
   - token_prefix: sk_live_abc...

💡 Suggestions:
   - Check your API token is valid
   - Run 'rgrid login' to authenticate
   - Verify you have permission for this resource
   - Contact support if the issue persists
```

**Cause**: API token is invalid, expired, or missing.

**Resolution**:
1. Login again: `rgrid login`
2. Check your API token in settings
3. Ensure the token has correct permissions
4. Generate a new token if needed

---

## ResourceNotFoundError

**Category**: Resource Not Found

**When It Occurs**: A requested resource doesn't exist.

**HTTP Status Code**: 404 Not Found

### Example

```
❌ Resource Not Found Error: Execution not found

   Context:
   - execution_id: exec-nonexistent
   - hint: Use 'rgrid list' to see available executions

💡 Suggestions:
   - Verify the resource ID is correct
   - Check the resource hasn't been deleted
   - Use 'rgrid list' to see available resources
```

**Cause**: The execution ID, job ID, or other resource doesn't exist.

**Resolution**:
1. Verify the ID is correct (check for typos)
2. List available resources: `rgrid list`
3. Check if the resource was deleted
4. Ensure you're in the correct project

---

## QuotaExceededError

**Category**: Quota/Rate Limit

**When It Occurs**: User exceeds quota or rate limits.

**HTTP Status Code**: 429 Too Many Requests

### Common Scenarios

#### Too Many Concurrent Jobs

```
❌ Quota Exceeded Error: Too many concurrent jobs

   Context:
   - current_jobs: 10
   - max_allowed: 10
   - plan: free

💡 Suggestions:
   - Wait for existing jobs to complete
   - Upgrade your plan for higher limits
   - Delete old artifacts to free up storage
   - Contact support to discuss quota increases
```

**Cause**: You've hit your plan's concurrent job limit.

**Resolution**:
1. Wait for some jobs to complete
2. Cancel unnecessary jobs: `rgrid cancel <exec_id>`
3. Upgrade to a higher plan for more capacity
4. Contact support for quota increase

---

#### Storage Quota Exceeded

```
❌ Quota Exceeded Error: Storage quota exceeded

   Context:
   - used_gb: 10.5
   - quota_gb: 10.0
   - plan: starter

💡 Suggestions:
   - Wait for existing jobs to complete
   - Upgrade your plan for higher limits
   - Delete old artifacts to free up storage
```

**Cause**: Your stored artifacts exceed your plan's storage limit.

**Resolution**:
1. Delete old executions: `rgrid delete <exec_id>`
2. Clean up artifacts you no longer need
3. Upgrade to a plan with more storage
4. Enable auto-cleanup in project settings

---

## API Response Format

All errors returned by the API follow this JSON structure:

```json
{
  "error_type": "ValidationError",
  "message": "Script file not found",
  "context": {
    "file": "nonexistent.py",
    "location": "/home/user/projects"
  },
  "timestamp": "2025-01-15T10:30:45.123Z"
}
```

---

## CLI Error Display

The CLI formats errors with:
- ❌ Error type and message
- Context information (if available)
- 💡 Suggestions for resolution

Example:

```
❌ Validation Error: Script file not found

   Context:
   - file: nonexistent.py
   - location: /home/user/projects

💡 Suggestions:
   - Check the file path is correct
   - Ensure the file exists in the current directory
   - Use absolute path if the file is elsewhere
```

---

## Debugging Tips

### Enable Debug Logging

Set environment variable for detailed logs:

```bash
export RGRID_DEBUG=1
rgrid run script.py
```

### View Full Stack Traces

For development, view raw errors:

```bash
rgrid run script.py --debug
```

### Check API Status

Verify RGrid services are operational:

```bash
curl https://api.rgrid.io/health
```

---

## Getting Help

If you encounter an error not covered here:

1. Check the logs: `rgrid logs <exec_id>`
2. Search the documentation: https://docs.rgrid.com
3. Visit the status page: https://status.rgrid.com
4. Contact support: support@rgrid.io
5. File a bug report: https://github.com/rgrid/rgrid/issues

---

**Last Updated**: 2025-01-16 (Tier 3 - Story 10-4)
