"""
Test development environment setup.

Story 1.2: Set Up Development Environment and Build System
"""

import pytest
from pathlib import Path
import tomllib


@pytest.fixture
def repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent


class TestPreCommitConfiguration:
    """Test pre-commit hook configuration."""

    def test_precommit_config_exists(self, repo_root: Path) -> None:
        """Verify .pre-commit-config.yaml exists."""
        precommit_path = repo_root / ".pre-commit-config.yaml"
        assert precommit_path.exists(), ".pre-commit-config.yaml should exist"

    def test_precommit_config_has_required_hooks(self, repo_root: Path) -> None:
        """Verify pre-commit config includes required hooks."""
        import yaml

        precommit_path = repo_root / ".pre-commit-config.yaml"

        # Install pyyaml if not available
        try:
            with open(precommit_path) as f:
                config = yaml.safe_load(f)
        except ImportError:
            pytest.skip("pyyaml not installed")

        repos = config.get("repos", [])
        hook_ids = []

        for repo in repos:
            for hook in repo.get("hooks", []):
                hook_ids.append(hook["id"])

        # Verify required hooks are present
        required_hooks = ["black", "ruff", "mypy"]
        for hook in required_hooks:
            assert hook in hook_ids, f"Hook {hook} should be in pre-commit config"


class TestDockerCompose:
    """Test Docker Compose configuration."""

    def test_docker_compose_exists(self, repo_root: Path) -> None:
        """Verify docker-compose.yml exists."""
        compose_path = repo_root / "infra" / "docker-compose.yml"
        assert compose_path.exists(), "infra/docker-compose.yml should exist"

    def test_docker_compose_has_required_services(self, repo_root: Path) -> None:
        """Verify docker-compose.yml includes PostgreSQL and MinIO."""
        import yaml

        compose_path = repo_root / "infra" / "docker-compose.yml"

        try:
            with open(compose_path) as f:
                config = yaml.safe_load(f)
        except ImportError:
            pytest.skip("pyyaml not installed")

        services = config.get("services", {})

        # Verify required services
        assert "postgres" in services, "PostgreSQL service should be defined"
        assert "minio" in services, "MinIO service should be defined"

        # Verify PostgreSQL configuration
        postgres = services["postgres"]
        assert "postgres:15" in postgres["image"], "Should use PostgreSQL 15"
        # Check if port 5432 or 5433 is exposed (5433 avoids conflicts)
        ports = str(postgres["ports"])
        assert "5432" in ports or "5433" in ports, "Should expose PostgreSQL port"

        # Verify MinIO configuration
        minio = services["minio"]
        assert "minio/minio" in minio["image"], "Should use MinIO image"
        assert "9000:9000" in minio["ports"], "Should expose port 9000"


class TestEnvironmentConfiguration:
    """Test environment configuration templates."""

    def test_env_example_exists(self, repo_root: Path) -> None:
        """Verify .env.example exists."""
        env_example_path = repo_root / ".env.example"
        assert env_example_path.exists(), ".env.example should exist"

    def test_env_example_has_required_vars(self, repo_root: Path) -> None:
        """Verify .env.example includes required variables."""
        env_example_path = repo_root / ".env.example"
        content = env_example_path.read_text()

        required_vars = [
            "DATABASE_URL",
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "API_HOST",
            "API_PORT",
        ]

        for var in required_vars:
            assert var in content, f"{var} should be in .env.example"


class TestMakefileTargets:
    """Test Makefile has required targets."""

    def test_makefile_has_setup_target(self, repo_root: Path) -> None:
        """Verify Makefile has setup target."""
        makefile_path = repo_root / "Makefile"
        content = makefile_path.read_text()

        assert "setup:" in content, "Makefile should have 'setup' target"
        assert "install-common" in content, "setup should install common package"
        assert "pre-commit install" in content, "setup should install pre-commit hooks"

    def test_makefile_has_dev_target(self, repo_root: Path) -> None:
        """Verify Makefile has dev target."""
        makefile_path = repo_root / "Makefile"
        content = makefile_path.read_text()

        assert "dev:" in content, "Makefile should have 'dev' target"
        assert "docker-compose" in content, "dev target should use docker-compose"

    def test_makefile_has_test_target(self, repo_root: Path) -> None:
        """Verify Makefile has test target."""
        makefile_path = repo_root / "Makefile"
        content = makefile_path.read_text()

        assert "test:" in content, "Makefile should have 'test' target"
        assert "pytest" in content, "test target should run pytest"


class TestPythonDependencies:
    """Test that Python dependencies are properly specified."""

    def test_api_dependencies_include_fastapi(self, repo_root: Path) -> None:
        """Verify API dependencies include FastAPI and related packages."""
        pyproject_path = repo_root / "api" / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        deps = config["project"]["dependencies"]

        # Check for key dependencies
        assert any("fastapi" in dep for dep in deps), "API should depend on fastapi"
        assert any("uvicorn" in dep for dep in deps), "API should depend on uvicorn"
        assert any("sqlalchemy" in dep for dep in deps), "API should depend on sqlalchemy"
        assert any("asyncpg" in dep for dep in deps), "API should depend on asyncpg"

    def test_cli_dependencies_include_click(self, repo_root: Path) -> None:
        """Verify CLI dependencies include Click."""
        pyproject_path = repo_root / "cli" / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        deps = config["project"]["dependencies"]

        assert any("click" in dep for dep in deps), "CLI should depend on click"
        assert any("httpx" in dep for dep in deps), "CLI should depend on httpx"
        assert any("rich" in dep for dep in deps), "CLI should depend on rich"

    def test_runner_dependencies_include_docker(self, repo_root: Path) -> None:
        """Verify runner dependencies include Docker SDK."""
        pyproject_path = repo_root / "runner" / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        deps = config["project"]["dependencies"]

        assert any("docker" in dep for dep in deps), "Runner should depend on docker"
        assert any("boto3" in dep for dep in deps), "Runner should depend on boto3"
