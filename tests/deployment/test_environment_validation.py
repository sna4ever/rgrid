"""
Deployment validation tests for environment configuration.

These tests catch environment variable issues before deployment.
"""

import os
from pathlib import Path


class TestEnvironmentConfiguration:
    """Validate environment variable configuration."""

    def test_database_url_format_documented(self):
        """Verify documentation shows correct async database URL format.

        CRITICAL: postgresql:// uses sync driver (psycopg2)
        REQUIRED: postgresql+asyncpg:// for FastAPI async operations
        """
        # Check example env files use correct format
        repo_root = Path(__file__).parent.parent.parent

        # Look for any .env.example or similar documentation
        example_files = list(repo_root.rglob(".env.example")) + \
                       list(repo_root.rglob("*.env.example")) + \
                       [repo_root / "TIER3_DEPLOYMENT_PLAN.md"]

        for env_file in example_files:
            if not env_file.exists():
                continue

            content = env_file.read_text()

            if "DATABASE_URL" in content:
                # If it mentions DATABASE_URL, it should use asyncpg
                assert "postgresql+asyncpg://" in content or "asyncpg" in content, (
                    f"{env_file.name} shows incorrect DATABASE_URL format!\n"
                    f"Must use: postgresql+asyncpg://user:pass@host:port/db\n"
                    f"NOT:      postgresql://user:pass@host:port/db\n"
                    f"\n"
                    f"FastAPI requires async driver (asyncpg).\n"
                    f"Alembic uses sync driver (psycopg2) but constructs its own URL."
                )

    def test_required_environment_variables_documented(self):
        """Verify all required environment variables are documented."""
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            # Not yet created, skip
            return

        content = deployment_plan.read_text()

        required_vars = [
            'DATABASE_URL',
            'MINIO_ENDPOINT',
            'MINIO_ACCESS_KEY',
            'MINIO_SECRET_KEY',
            'MINIO_BUCKET_NAME',
            'API_SECRET_KEY',
            'RAY_ENABLED',
        ]

        for var in required_vars:
            assert var in content, (
                f"Required environment variable {var} not documented in deployment plan!\n"
                f"This causes runtime failures when deploying."
            )

    def test_ray_enabled_defaults_to_false_for_tier3(self):
        """Verify RAY_ENABLED is documented as false for Tier 3.

        RAY is a Tier 4+ feature. Must be disabled in Tier 3.
        """
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        if "RAY_ENABLED" in content:
            # Should be set to false in Tier 3 examples
            assert "RAY_ENABLED=false" in content, (
                "RAY_ENABLED should be false in Tier 3 deployment examples\n"
                "Ray is a Tier 4+ feature."
            )


class TestDependencyConfiguration:
    """Validate dependency installation requirements."""

    def test_both_database_drivers_required(self):
        """Verify both asyncpg and psycopg2-binary are documented.

        asyncpg: FastAPI async operations
        psycopg2-binary: Alembic sync migrations
        """
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        # Should mention both drivers are needed
        has_asyncpg = "asyncpg" in content
        has_psycopg2 = "psycopg2" in content or "psycopg2-binary" in content

        if has_asyncpg or has_psycopg2:
            # If it mentions one, should mention both
            assert has_asyncpg and has_psycopg2, (
                "Deployment docs should mention BOTH database drivers:\n"
                "- asyncpg: For FastAPI async operations\n"
                "- psycopg2-binary: For Alembic migrations\n"
                "\n"
                "Missing one will cause runtime errors!"
            )

    def test_ray_installation_documented_as_optional(self):
        """Verify Ray installation is documented but marked as optional/disabled."""
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        if "pip install" in content and "ray" in content.lower():
            # Should mention it's for Tier 4+ or disabled
            assert "Tier 4" in content or "disabled" in content or "RAY_ENABLED=false" in content, (
                "Ray installation should be marked as Tier 4+ or disabled in Tier 3"
            )


class TestSystemdServiceConfiguration:
    """Validate systemd service file correctness."""

    def test_systemd_uses_correct_module_path(self):
        """Verify systemd ExecStart lines use app.main:app not api.main:app.

        When WorkingDirectory=/home/deploy/rgrid/api, the module path
        is relative to that directory, so it's app.main:app not api.main:app.

        Note: The docs may mention 'api.main:app' in explanatory context
        (e.g., "don't use api.main:app"), so we check ExecStart lines specifically.
        """
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        # If it shows systemd service, check module path
        if "ExecStart" in content and "uvicorn" in content:
            # Check that ExecStart lines use app.main:app
            # Note: api.main:app may appear in explanatory text about what NOT to do
            for line in content.split('\n'):
                if 'ExecStart' in line and 'uvicorn' in line:
                    # ExecStart line should use app.main:app, not api.main:app
                    assert 'api.main:app' not in line, (
                        f"ExecStart line uses wrong module path!\n"
                        f"Line: {line}\n"
                        f"When WorkingDirectory=/home/deploy/rgrid/api\n"
                        f"Use:  app.main:app\n"
                        f"NOT:  api.main:app"
                    )

            # Should use app.main:app in ExecStart lines
            if "WorkingDirectory" in content and "/rgrid/api" in content:
                assert "app.main:app" in content, (
                    "Systemd service should use app.main:app when WorkingDirectory is /rgrid/api"
                )


class TestPortAssignments:
    """Validate port assignments to avoid conflicts."""

    def test_port_assignments_documented(self):
        """Verify port assignments are clearly documented.

        Critical ports:
        - 8000: Production API
        - 8001: Staging API
        - 9443: Portainer (HTTPS only, NOT 8000!)
        """
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        # Should document port assignments
        if "port" in content.lower():
            # Production API should be on 8000
            if "production" in content.lower() and "api" in content.lower():
                assert ":8000" in content, "Production API should be on port 8000"

            # Staging API should be on 8001
            if "staging" in content.lower() and "api" in content.lower():
                assert ":8001" in content, "Staging API should be on port 8001"

    def test_portainer_port_conflict_documented(self):
        """Verify Portainer port conflict issue is documented.

        Portainer defaults to ports 9443 AND 8000.
        Port 8000 conflicts with Production API.
        Must only expose port 9443.
        """
        deployment_plan = Path(__file__).parent.parent.parent / "docs" / "TIER3_DEPLOYMENT_PLAN.md"

        if not deployment_plan.exists():
            return

        content = deployment_plan.read_text()

        # If Portainer is mentioned, should document correct port usage
        if "portainer" in content.lower():
            # Should mention 9443
            assert "9443" in content, "Portainer HTTPS port (9443) not documented"

            # Should warn about 8000 conflict OR only show 9443
            if "8000" in content and "portainer" in content.lower():
                # Make sure it's warning about the conflict, not telling users to use 8000
                portainer_section = content.lower()
                assert "conflict" in portainer_section or "only" in portainer_section, (
                    "Deployment docs should warn about Portainer port 8000 conflict with Production API"
                )
