"""Unit tests for requirements.txt detection and handling (Story 2.4)."""

import pytest
from pathlib import Path
import tempfile
import os


class TestRequirementsDetection:
    """Test requirements.txt detection in script directory."""

    def test_detect_requirements_in_same_directory(self):
        """Should find requirements.txt in same directory as script."""
        from rgrid.utils.file_detection import detect_requirements_file

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create script and requirements.txt in same directory
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("print('hello')")

            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0\npandas==2.0.0")

            # Act
            result = detect_requirements_file(str(script_path))

            # Assert
            assert result is not None
            assert result == str(requirements_path)

    def test_no_requirements_file_returns_none(self):
        """Should return None when requirements.txt doesn't exist."""
        from rgrid.utils.file_detection import detect_requirements_file

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only script
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("print('hello')")

            # Act
            result = detect_requirements_file(str(script_path))

            # Assert
            assert result is None

    def test_requirements_in_different_directory_not_found(self):
        """Should not find requirements.txt in different directory."""
        from rgrid.utils.file_detection import detect_requirements_file

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirectory structure
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            # Script in subdir
            script_path = subdir / "script.py"
            script_path.write_text("print('hello')")

            # Requirements.txt in parent dir (should NOT be found)
            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("numpy==1.24.0")

            # Act
            result = detect_requirements_file(str(script_path))

            # Assert
            assert result is None


class TestRequirementsFileHandling:
    """Test requirements.txt file upload and parsing."""

    def test_parse_valid_requirements_file(self):
        """Should parse valid requirements.txt content."""
        from rgrid.utils.file_detection import parse_requirements_content

        content = "numpy==1.24.0\npandas==2.0.0\nscikit-learn>=1.0.0"

        # Act
        result = parse_requirements_content(content)

        # Assert
        assert result is True  # Valid format

    def test_parse_empty_requirements_file(self):
        """Should handle empty requirements.txt."""
        from rgrid.utils.file_detection import parse_requirements_content

        content = ""

        # Act
        result = parse_requirements_content(content)

        # Assert
        assert result is True  # Empty is valid

    def test_parse_requirements_with_comments(self):
        """Should handle requirements.txt with comments."""
        from rgrid.utils.file_detection import parse_requirements_content

        content = """# Data processing
numpy==1.24.0
# Analysis
pandas==2.0.0"""

        # Act
        result = parse_requirements_content(content)

        # Assert
        assert result is True  # Comments are valid
