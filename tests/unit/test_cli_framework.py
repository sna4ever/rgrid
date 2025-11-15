"""
Test CLI framework.

Story 1.4: Build CLI Framework with Click
"""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_entry_point_exists(self) -> None:
        """Test that rgrid CLI module can be imported."""
        from rgrid.cli import main

        assert main is not None

    def test_cli_help(self, cli_runner: CliRunner) -> None:
        """Test CLI help command."""
        from rgrid.cli import main

        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "RGrid" in result.output
        assert "Run Python scripts remotely" in result.output

    def test_cli_version(self, cli_runner: CliRunner) -> None:
        """Test CLI version flag."""
        from rgrid.cli import main

        result = cli_runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_version_command(self, cli_runner: CliRunner) -> None:
        """Test version subcommand."""
        from rgrid.cli import main

        result = cli_runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
