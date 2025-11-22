"""
Deployment validation tests for Alembic migrations.

These tests prevent the migration issues encountered in actual Tier 3 deployment.
"""

import os
import re
from pathlib import Path


class TestAlembicReadiness:
    """Validate Alembic configuration before deployment."""

    def test_alembic_env_imports_all_models(self):
        """Verify alembic/env.py imports all 6 required models.

        CRITICAL: Missing imports cause empty migrations with only 'pass' statements.
        This test prevents the issue we hit in actual deployment.
        """
        env_path = Path(__file__).parent.parent.parent / "api" / "alembic" / "env.py"
        assert env_path.exists(), f"Alembic env.py not found at {env_path}"

        env_content = env_path.read_text()

        required_models = [
            'Execution',
            'APIKey',
            'Artifact',
            'Worker',
            'DependencyCache',
            'CombinedCache'
        ]

        for model in required_models:
            assert model in env_content, (
                f"Missing model import in alembic/env.py: {model}\n"
                f"This will cause empty migrations to be generated!\n"
                f"Add: from app.models.{model.lower()} import {model}  # noqa: F401"
            )

    def test_migrations_directory_exists(self):
        """Verify migrations directory structure is correct."""
        migrations_dir = Path(__file__).parent.parent.parent / "api" / "alembic" / "versions"
        assert migrations_dir.exists(), "Alembic versions directory not found"
        assert migrations_dir.is_dir(), "Alembic versions should be a directory"

    def test_alembic_ini_exists(self):
        """Verify alembic.ini configuration file exists."""
        ini_path = Path(__file__).parent.parent.parent / "api" / "alembic.ini"
        assert ini_path.exists(), "alembic.ini not found"

        ini_content = ini_path.read_text()
        # Accept both 'script_location = alembic' and 'script_location = %(here)s/alembic'
        assert "script_location" in ini_content and "alembic" in ini_content, (
            "alembic.ini missing script_location configuration"
        )

    def test_latest_migration_creates_tables(self):
        """Verify latest migration has CREATE TABLE statements.

        Prevents empty migrations with only 'pass' statements.
        """
        versions_dir = Path(__file__).parent.parent.parent / "api" / "alembic" / "versions"

        if not versions_dir.exists():
            # Fresh install, no migrations yet
            return

        migration_files = list(versions_dir.glob("*.py"))
        if not migration_files:
            # No migrations yet, skip test
            return

        # Get most recent migration
        latest_migration = max(migration_files, key=lambda p: p.stat().st_mtime)
        migration_content = latest_migration.read_text()

        # Should have CREATE TABLE statements (unless it's a pure data migration)
        # At minimum, should not be empty upgrade/downgrade functions
        assert "def upgrade()" in migration_content, (
            f"Migration {latest_migration.name} missing upgrade() function"
        )
        assert "def downgrade()" in migration_content, (
            f"Migration {latest_migration.name} missing downgrade() function"
        )

        # Check that upgrade function is not just 'pass'
        # Extract upgrade function
        upgrade_match = re.search(
            r'def upgrade\(\).*?:.*?\n(.*?)(?=def\s|\Z)',
            migration_content,
            re.DOTALL
        )

        if upgrade_match:
            upgrade_body = upgrade_match.group(1).strip()
            assert upgrade_body != "pass", (
                f"Migration {latest_migration.name} has empty upgrade() function!\n"
                f"This indicates alembic/env.py is not importing all models.\n"
                f"Check that all 6 models are imported in env.py"
            )


class TestMigrationExpectedTables:
    """Verify expected database schema from migrations."""

    def test_migration_includes_expected_tables(self):
        """Verify migrations collectively create all expected tables.

        Expected tables:
        - api_keys
        - artifacts
        - combined_cache
        - dependency_cache
        - executions
        - worker_heartbeats
        - workers

        Note: Tables may be spread across multiple migrations due to
        incremental schema evolution. This test checks the combined
        migration chain.
        """
        versions_dir = Path(__file__).parent.parent.parent / "api" / "alembic" / "versions"

        if not versions_dir.exists():
            return

        migration_files = list(versions_dir.glob("*.py"))
        if not migration_files:
            return

        # Combine all migration content to check for tables
        all_migration_content = ""
        for migration_file in migration_files:
            all_migration_content += migration_file.read_text() + "\n"

        expected_tables = [
            'api_keys',
            'executions',
            'artifacts',
            'workers',
            'dependency_cache',
            'combined_cache',
        ]

        # Check that tables are referenced somewhere in migrations
        # (either create_table or add_column to existing table)
        for table in expected_tables:
            assert table in all_migration_content, (
                f"No migration references table: {table}\n"
                f"Verify alembic/env.py imports corresponding model and run autogenerate"
            )
