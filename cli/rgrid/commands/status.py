"""Status command for checking execution status."""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime

from rgrid.api_client import get_client

# Import structured error handling (Story 10-4)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "api"))
from api.errors import ResourceNotFoundError, NetworkError
from rgrid.errors import display_error

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
        elif status_value == "queued":
            # Enhanced feedback for queued status (Story NEW-4)
            status_display = f"[yellow]{status_value}[/yellow]"
            # Calculate how long it's been queued
            created_at = datetime.fromisoformat(result["created_at"].replace('Z', '+00:00'))
            queued_duration = (datetime.now(created_at.tzinfo) - created_at).total_seconds()

            if queued_duration > 30:
                # If queued for more than 30 seconds, likely provisioning workers
                elapsed_min = int(queued_duration // 60)
                elapsed_sec = int(queued_duration % 60)
                if elapsed_min > 0:
                    time_display = f"{elapsed_min}m {elapsed_sec}s"
                else:
                    time_display = f"{elapsed_sec}s"

                status_display += f"\n[dim]Provisioning worker... ({time_display} elapsed, ETA ~90s)[/dim]"
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
        # Use structured error handling (Story 10-4)
        error_msg = str(e).lower()

        if "not found" in error_msg or "404" in error_msg:
            error = ResourceNotFoundError(
                "Execution not found",
                context={
                    "execution_id": execution_id,
                    "hint": "Use 'rgrid list' to see available executions"
                }
            )
            display_error(error)
        elif "connection" in error_msg or "network" in error_msg:
            error = NetworkError(
                "Failed to connect to API",
                context={
                    "execution_id": execution_id,
                    "error": str(e)
                }
            )
            display_error(error)
        else:
            # Generic error display
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
