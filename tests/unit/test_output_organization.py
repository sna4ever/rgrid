"""Unit tests for batch output organization (Tier 5 - Story 5-4)."""

import pytest
import os
import tempfile
from pathlib import Path


class TestInputNameExtraction:
    """Test extracting input filename from execution metadata."""

    def test_extract_input_name(self):
        """Get filename from metadata."""
        from cli.rgrid.batch_download import extract_input_name

        # Arrange
        execution = {"batch_metadata": {"input_file": "data.csv"}}

        # Act
        result = extract_input_name(execution)

        # Assert
        assert result == "data.csv"

    def test_extract_input_name_from_path(self):
        """Extract just filename from full path."""
        from cli.rgrid.batch_download import extract_input_name

        # Arrange
        execution = {"batch_metadata": {"input_file": "/path/to/data.csv"}}

        # Act
        result = extract_input_name(execution)

        # Assert
        assert result == "data.csv"

    def test_extract_input_name_missing(self):
        """Handle missing input file metadata."""
        from cli.rgrid.batch_download import extract_input_name

        # Arrange
        execution = {}

        # Act
        result = extract_input_name(execution)

        # Assert
        assert result is None or result == "unknown"


class TestOutputDirectoryCreation:
    """Test creating output directories."""

    def test_create_output_directory(self):
        """Make ./outputs/input1/ directory."""
        from cli.rgrid.batch_download import create_output_directory

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = tmpdir
            input_name = "data.csv"

            # Act
            result = create_output_directory(base_dir, input_name, flat=False)

            # Assert
            expected = os.path.join(base_dir, "data.csv")
            assert result == expected
            assert os.path.exists(result)
            assert os.path.isdir(result)

    def test_custom_output_dir(self):
        """--output-dir flag works."""
        from cli.rgrid.batch_download import create_output_directory

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = os.path.join(tmpdir, "custom", "location")
            input_name = "file.txt"

            # Act
            result = create_output_directory(custom_dir, input_name, flat=False)

            # Assert
            expected = os.path.join(custom_dir, "file.txt")
            assert result == expected
            assert os.path.exists(result)

    def test_flat_flag(self):
        """--flat disables subdirectories."""
        from cli.rgrid.batch_download import create_output_directory

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = tmpdir
            input_name = "data.csv"

            # Act
            result = create_output_directory(base_dir, input_name, flat=True)

            # Assert
            # Should return base_dir, not create subdirectory
            assert result == base_dir
            # Only base_dir should exist, no subdirectory for input_name
            assert not os.path.exists(os.path.join(base_dir, "data.csv"))


class TestDuplicateHandling:
    """Test handling duplicate input names."""

    def test_handle_duplicate_names(self):
        """data.csv → data.csv, data_1.csv when collision."""
        from cli.rgrid.batch_download import sanitize_output_dirname

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = tmpdir
            # Create first directory
            first_dir = os.path.join(base_dir, "data.csv")
            os.makedirs(first_dir)

            # Act - Try to create second with same name
            result = sanitize_output_dirname(base_dir, "data.csv")

            # Assert
            # Should append counter to avoid collision
            assert result == "data_1.csv" or "data.csv" in result
            assert result != "data.csv"  # Must be different

    def test_sanitize_removes_special_chars(self):
        """Remove unsafe characters from directory names."""
        from cli.rgrid.batch_download import sanitize_output_dirname

        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = tmpdir

            # Act
            result = sanitize_output_dirname(base_dir, "file:with*bad<chars>.csv")

            # Assert
            # Should remove or replace special characters
            assert ":" not in result
            assert "*" not in result
            assert "<" not in result
            assert ">" not in result


class TestOutputPathConstruction:
    """Test constructing output file paths."""

    def test_preserve_subdirectory_structure(self):
        """Preserve output subdirectories: /work/results/output.csv → ./outputs/input1/results/output.csv"""
        from cli.rgrid.batch_download import construct_output_path

        # Arrange
        output_dir = "/tmp/outputs/input1"
        artifact_path = "/work/results/output.csv"  # Path in container

        # Act
        result = construct_output_path(output_dir, artifact_path)

        # Assert
        # Should preserve "results" subdirectory
        assert result == "/tmp/outputs/input1/results/output.csv"

    def test_flat_output_path(self):
        """Flat mode ignores subdirectories."""
        from cli.rgrid.batch_download import construct_output_path

        # Arrange
        output_dir = "/tmp/outputs"
        artifact_path = "/work/results/deep/nested/output.csv"

        # Act
        result = construct_output_path(output_dir, artifact_path, preserve_structure=False)

        # Assert
        # Should flatten to just filename
        assert result == "/tmp/outputs/output.csv"

    def test_handle_absolute_artifact_paths(self):
        """Handle absolute paths in artifact metadata."""
        from cli.rgrid.batch_download import construct_output_path

        # Arrange
        output_dir = "/tmp/outputs/input1"
        artifact_path = "/work/output.txt"

        # Act
        result = construct_output_path(output_dir, artifact_path)

        # Assert
        assert result == "/tmp/outputs/input1/output.txt"
