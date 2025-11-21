"""Unit tests for auto-upload file detection (Story 7-1).

Tests cover:
- CLI detects arguments that are local file paths
- Non-file arguments (strings, numbers) are passed as-is
- Transforms paths to /work/filename for container
- Handles flags (--flag) correctly
- Handles mixed arguments (files and strings together)
- Error handling for explicit file paths that don't exist
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from rgrid.utils.file_detection import detect_file_arguments


class TestDetectFileArguments:
    """Test file argument detection for Story 7-1."""

    def test_detects_existing_file(self):
        """When argument is an existing file, should detect it."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            temp_file = f.name

        try:
            args = [temp_file, 'regular_arg']

            # Act
            file_args, regular_args = detect_file_arguments(args)

            # Assert
            assert temp_file in file_args, "Existing file should be detected as file arg"
            assert 'regular_arg' in regular_args
        finally:
            os.unlink(temp_file)

    def test_ignores_nonexistent_path(self):
        """When argument looks like a path but doesn't exist, treat as regular arg."""
        # Arrange
        args = ['/nonexistent/file.json', 'regular_arg']

        # Act
        file_args, regular_args = detect_file_arguments(args)

        # Assert
        assert len(file_args) == 0, "Non-existent paths should not be files"
        assert '/nonexistent/file.json' in regular_args

    def test_ignores_string_args(self):
        """Non-path strings should be passed through unchanged."""
        # Arrange
        args = ['--output', 'value', '123', 'string_arg']

        # Act
        file_args, regular_args = detect_file_arguments(args)

        # Assert
        assert len(file_args) == 0
        assert '--output' in regular_args
        assert 'value' in regular_args
        assert '123' in regular_args
        assert 'string_arg' in regular_args

    def test_handles_flags(self):
        """Arguments starting with - or -- should not be treated as files."""
        # Arrange
        args = ['--output', '-v', '--flag=value']

        # Act
        file_args, regular_args = detect_file_arguments(args)

        # Assert
        assert len(file_args) == 0, "Flags should not be detected as files"
        assert '--output' in regular_args
        assert '-v' in regular_args
        assert '--flag=value' in regular_args

    def test_handles_mixed_args(self):
        """Should correctly separate files from regular args in mixed input."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f1, \
             tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f2:
            f1.write('col1,col2\n1,2')
            f2.write('{"key": "value"}')
            file1 = f1.name
            file2 = f2.name

        try:
            args = [file1, '--output', 'result.txt', file2, 'regular_string']

            # Act
            file_args, regular_args = detect_file_arguments(args)

            # Assert
            assert file1 in file_args
            assert file2 in file_args
            assert len(file_args) == 2
            assert '--output' in regular_args
            assert 'result.txt' in regular_args
            assert 'regular_string' in regular_args
        finally:
            os.unlink(file1)
            os.unlink(file2)


class TestPathTransformation:
    """Test path transformation to /work/filename (Runner side)."""

    def test_transforms_path_to_work_dir(self):
        """File paths should be transformed to /work/filename."""
        from runner.runner.file_handler import map_args_to_container_paths

        # Arrange
        original_args = ['input.json', '--flag', 'value']
        input_files = ['input.json']

        # Act
        container_args = map_args_to_container_paths(original_args, input_files)

        # Assert
        assert '/work/input.json' in container_args
        assert '--flag' in container_args
        assert 'value' in container_args

    def test_transforms_full_path_to_work_dir(self):
        """Full file paths like /tmp/data.csv should become /work/data.csv."""
        from runner.runner.file_handler import map_args_to_container_paths

        # Arrange - args as they would be after CLI detection
        original_args = ['/tmp/data.csv', 'output.txt']
        input_files = ['data.csv']  # Just the filename, not full path

        # Act
        container_args = map_args_to_container_paths(original_args, input_files)

        # Assert
        assert '/work/data.csv' in container_args
        assert 'output.txt' in container_args

    def test_preserves_non_file_args(self):
        """Non-file args should be preserved unchanged."""
        from runner.runner.file_handler import map_args_to_container_paths

        # Arrange
        original_args = ['--output', 'results.json', '42', 'string']
        input_files = []  # No input files

        # Act
        container_args = map_args_to_container_paths(original_args, input_files)

        # Assert
        assert container_args == ['--output', 'results.json', '42', 'string']


class TestMissingFileError:
    """Test error handling for missing files."""

    def test_validate_file_args_raises_on_missing_explicit_file(self):
        """When user specifies a file path that doesn't exist, should raise error."""
        from rgrid.utils.file_detection import validate_file_args

        # Arrange - path that looks like a file but doesn't exist
        args = ['/path/to/missing.csv', 'regular_arg']

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_file_args(args)

        assert 'missing.csv' in str(exc_info.value)

    def test_validate_file_args_passes_for_existing_files(self):
        """When file exists, validation should pass."""
        from rgrid.utils.file_detection import validate_file_args

        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{}')
            temp_file = f.name

        try:
            args = [temp_file, 'regular_arg']

            # Act - should not raise
            result = validate_file_args(args)

            # Assert
            assert result is None  # No error
        finally:
            os.unlink(temp_file)

    def test_validate_file_args_ignores_non_path_strings(self):
        """Regular string args should not trigger file validation."""
        from rgrid.utils.file_detection import validate_file_args

        # Arrange - these look like strings, not file paths
        args = ['--output', 'value', '123', 'regular']

        # Act - should not raise
        result = validate_file_args(args)

        # Assert
        assert result is None
