"""Logs command for viewing execution output."""

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from rgrid.api_client import get_client

console = Console()


@click.command()
@click.argument("execution_id")
@click.option(
    "--stdout-only",
    is_flag=True,
    help="Show only stdout",
)
@click.option(
    "--stderr-only",
    is_flag=True,
    help="Show only stderr",
)
def logs(execution_id: str, stdout_only: bool, stderr_only: bool) -> None:
    """
    View execution logs (stdout/stderr).

    Args:
        execution_id: Execution ID to view logs for
        stdout_only: Show only stdout
        stderr_only: Show only stderr
    """
    try:
        # Get API client
        client = get_client()

        # Fetch execution
        result = client.get_execution(execution_id)

        # Check if execution has output
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        output_truncated = result.get("output_truncated", False)

        if not stdout and not stderr:
            console.print("[yellow]No output available for this execution[/yellow]")
            return

        # Display stdout
        if stdout and not stderr_only:
            if stdout_only or stderr:
                console.print("\n[bold cyan]STDOUT:[/bold cyan]")
            console.print(stdout.rstrip())

        # Display stderr
        if stderr and not stdout_only:
            if stderr_only or stdout:
                console.print("\n[bold red]STDERR:[/bold red]")
            console.print(f"[red]{stderr.rstrip()}[/red]")

        # Show truncation warning
        if output_truncated:
            console.print(
                "\n[yellow]⚠ Output was truncated (exceeded 100KB limit)[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()
