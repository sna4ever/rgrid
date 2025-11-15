"""Status command for checking execution status."""

import click
from rich.console import Console
from rich.table import Table
from datetime import datetime

from rgrid.api_client import get_client

console = Console()


@click.command()
@click.argument("execution_id")
def status(execution_id: str) -> None:
    """
    Check the status of an execution.

    Args:
        execution_id: Execution ID to check
    """
    try:
        # Get API client
        client = get_client()

        # Fetch execution status
        result = client.get_execution(execution_id)

        # Display results
        console.print(f"\n[bold]Execution: {execution_id}[/bold]\n")

        # Create status table
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        # Status with color coding
        status_value = result["status"]
        if status_value == "completed":
            status_display = f"[green]{status_value}[/green]"
        elif status_value == "failed":
            status_display = f"[red]{status_value}[/red]"
        elif status_value == "running":
            status_display = f"[yellow]{status_value}[/yellow]"
        else:
            status_display = status_value

        table.add_row("Status", status_display)
        table.add_row("Runtime", result["runtime"])

        # Timestamps
        created_at = result["created_at"]
        table.add_row("Created", _format_timestamp(created_at))

        if result.get("started_at"):
            table.add_row("Started", _format_timestamp(result["started_at"]))

        if result.get("completed_at"):
            table.add_row("Completed", _format_timestamp(result["completed_at"]))

            # Calculate duration
            started = datetime.fromisoformat(result["started_at"].replace('Z', '+00:00'))
            completed = datetime.fromisoformat(result["completed_at"].replace('Z', '+00:00'))
            duration = (completed - started).total_seconds()
            table.add_row("Duration", f"{duration:.1f}s")

        # Exit code
        if result.get("exit_code") is not None:
            exit_code = result["exit_code"]
            exit_display = f"[green]{exit_code}[/green]" if exit_code == 0 else f"[red]{exit_code}[/red]"
            table.add_row("Exit Code", exit_display)

        # Error message if failed
        if result.get("execution_error"):
            table.add_row("Error", f"[red]{result['execution_error']}[/red]")

        # Output info
        if result.get("stdout") or result.get("stderr"):
            has_output = "Yes"
            if result.get("output_truncated"):
                has_output += " [yellow](truncated)[/yellow]"
            table.add_row("Has Output", has_output)

        console.print(table)

        # Show hint for viewing logs
        if result.get("stdout") or result.get("stderr"):
            console.print(f"\n[dim]View output with:[/dim] rgrid logs {execution_id}\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


def _format_timestamp(ts_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        # Parse ISO format timestamp
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts_str
