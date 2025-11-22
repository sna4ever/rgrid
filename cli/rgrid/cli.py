"""
RGrid CLI - Main command-line interface.

Provides commands for running Python scripts remotely.
"""

import click
from rich.console import Console

from rgrid import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="rgrid")
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    RGrid - Run Python scripts remotely with zero friction.

    Examples:

        \b
        # Run a script remotely
        $ rgrid run script.py input.json

        \b
        # Run batch of scripts in parallel
        $ rgrid run process.py --batch data/*.csv --parallel 10

        \b
        # Check execution status
        $ rgrid status <execution-id>

    For more information, visit: https://docs.rgrid.dev
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@main.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]RGrid CLI[/bold] version [cyan]{__version__}[/cyan]")


# Import and register commands
from rgrid.commands.init import init
from rgrid.commands.run import run
from rgrid.commands.status import status
from rgrid.commands.logs import logs
from rgrid.commands.download import download
from rgrid.commands.cost import cost
from rgrid.commands.estimate import estimate
from rgrid.commands.retry import retry

main.add_command(init)
main.add_command(run)
main.add_command(status)
main.add_command(logs)
main.add_command(download)
main.add_command(cost)
main.add_command(estimate)
main.add_command(retry)


if __name__ == "__main__":
    main()
