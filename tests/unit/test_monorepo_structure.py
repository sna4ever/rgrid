"""
Test monorepo structure initialization.

Story 1.1: Initialize Monorepo Project Structure
"""

import pytest
from pathlib import Path
import tomllib


@pytest.fixture
def repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent


class TestDirectoryStructure:
    """Test that the monorepo directory structure is correct."""

    def test_root_directories_exist(self, repo_root: Path) -> None:
        """Verify all required root directories exist."""
        required_dirs = [
            "api",
            "orchestrator",
            "runner",
            "cli",
            "console",
            "website",
            "common",
            "infra",
            "tests",
            "docs",
        ]

        for dir_name in required_dirs:
            dir_path = repo_root / dir_name
            assert dir_path.exists(), f"Directory {dir_name}/ should exist"
            assert dir_path.is_dir(), f"{dir_name}/ should be a directory"

    def test_api_structure(self, repo_root: Path) -> None:
        """Verify API component structure."""
        api_path = repo_root / "api"
        assert (api_path / "app").exists()
        assert (api_path / "app" / "api" / "v1").exists()
        assert (api_path / "app" / "services").exists()
        assert (api_path / "app" / "schemas").exists()
        assert (api_path / "app" / "models").exists()

    def test_infra_structure(self, repo_root: Path) -> None:
        """Verify infra component structure."""
        infra_path = repo_root / "infra"
        assert (infra_path / "dockerfiles").exists()
        assert (infra_path / "terraform").exists()
        assert (infra_path / "cloud-init").exists()
        assert (infra_path / "docker-compose.yml").exists()

    def test_tests_structure(self, repo_root: Path) -> None:
        """Verify test directory structure."""
        tests_path = repo_root / "tests"
        assert (tests_path / "unit").exists()
        assert (tests_path / "integration").exists()
        assert (tests_path / "conftest.py").exists()


class TestRootFiles:
    """Test that root configuration files exist and are valid."""

    def test_root_files_exist(self, repo_root: Path) -> None:
        """Verify required root files exist."""
        required_files = [
            "pyproject.toml",
            ".gitignore",
            "README.md",
            "Makefile",
        ]

        for file_name in required_files:
            file_path = repo_root / file_name
            assert file_path.exists(), f"File {file_name} should exist"
            assert file_path.is_file(), f"{file_name} should be a file"

    def test_gitignore_excludes_sensitive_files(self, repo_root: Path) -> None:
        """Verify .gitignore excludes sensitive files."""
        gitignore_path = repo_root / ".gitignore"
        content = gitignore_path.read_text()

        required_exclusions = [
            "venv/",
            "__pycache__/",
            ".env",
            ".rgrid/",
            "*.secret",
            "*.key",
        ]

        for exclusion in required_exclusions:
            assert exclusion in content, f".gitignore should exclude {exclusion}"

    def test_root_pyproject_toml_valid(self, repo_root: Path) -> None:
        """Verify root pyproject.toml is valid TOML."""
        pyproject_path = repo_root / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        assert "project" in config
        assert config["project"]["name"] == "rgrid-monorepo"
        assert "tool" in config
        assert "black" in config["tool"]
        assert "ruff" in config["tool"]
        assert "mypy" in config["tool"]
        assert "pytest" in config["tool"]


class TestPythonPackages:
    """Test that Python packages are properly configured."""

    def test_component_pyproject_files_exist(self, repo_root: Path) -> None:
        """Verify each Python component has pyproject.toml."""
        components = ["api", "cli", "orchestrator", "runner", "common"]

        for component in components:
            pyproject_path = repo_root / component / "pyproject.toml"
            assert pyproject_path.exists(), f"{component}/pyproject.toml should exist"

    def test_component_pyproject_files_valid(self, repo_root: Path) -> None:
        """Verify component pyproject.toml files are valid."""
        components = {
            "api": "rgrid-api",
            "cli": "rgrid",
            "orchestrator": "rgrid-orchestrator",
            "runner": "rgrid-runner",
            "common": "rgrid-common",
        }

        for component, expected_name in components.items():
            pyproject_path = repo_root / component / "pyproject.toml"
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            assert "project" in config
            assert config["project"]["name"] == expected_name
            assert "dependencies" in config["project"]


class TestCommonPackage:
    """Test the shared common package."""

    def test_common_package_structure(self, repo_root: Path) -> None:
        """Verify common package structure."""
        common_path = repo_root / "common" / "rgrid_common"
        assert common_path.exists()
        assert (common_path / "__init__.py").exists()
        assert (common_path / "money.py").exists()
        assert (common_path / "types.py").exists()
        assert (common_path / "models.py").exists()

    def test_common_package_imports(self) -> None:
        """Test that common package can be imported."""
        try:
            from rgrid_common import Money, ExecutionStatus, RuntimeType

            assert Money is not None
            assert ExecutionStatus is not None
            assert RuntimeType is not None
        except ImportError as e:
            pytest.fail(f"Failed to import from rgrid_common: {e}")

    def test_money_class_basic_operations(self) -> None:
        """Test Money class basic operations."""
        from rgrid_common import Money

        # Create from micros
        m1 = Money(1500000)
        assert m1.micros == 1500000
        assert m1.to_eur() == 1.5

        # Create from EUR
        m2 = Money.from_eur(2.50)
        assert m2.micros == 2500000

        # Addition
        m3 = m1 + m2
        assert m3.micros == 4000000

        # Formatting
        assert m1.format() == "€1.50"

    def test_execution_status_enum(self) -> None:
        """Test ExecutionStatus enum."""
        from rgrid_common import ExecutionStatus

        assert ExecutionStatus.QUEUED.value == "queued"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"

    def test_runtime_type_enum(self) -> None:
        """Test RuntimeType enum."""
        from rgrid_common import RuntimeType

        assert RuntimeType.PYTHON_311.value == "python:3.11"
        assert RuntimeType.PYTHON_311.docker_image == "python:3.11"
