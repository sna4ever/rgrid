"""Estimate command for predicting batch execution costs (Story 9-4)."""

import glob
import click
from rich.console import Console
from rich.panel import Panel

from rgrid.api_client import get_client

console = Console()


@click.command()
@click.option(
    "--runtime",
    type=str,
    default="python:3.11",
    help="Runtime environment (e.g., python:3.11, node:20)",
)
@click.option(
    "--batch",
    type=str,
    default=None,
    help="Glob pattern for batch files (e.g., data/*.csv)",
)
@click.option(
    "--files",
    type=int,
    default=None,
    help="Number of files (alternative to --batch)",
)
def estimate(runtime: str, batch: str | None, files: int | None) -> None:
    """
    Estimate cost for batch execution before running.

    Uses historical execution data to predict cost based on median
    duration of similar executions.

    Examples:

        \b
        # Estimate cost for batch of CSV files
        $ rgrid estimate --batch data/*.csv

        \b
        # Estimate cost for specific runtime
        $ rgrid estimate --runtime node:20 --batch scripts/*.js

        \b
        # Estimate cost for specific file count
        $ rgrid estimate --files 100
    """
    try:
        # Determine file count
        if batch:
            # Expand glob pattern
            matched_files = glob.glob(batch)
            file_count = len(matched_files)
            if file_count == 0:
                console.print(f"[yellow]Warning:[/yellow] No files match pattern '{batch}'")
                console.print("Cost estimate will be for 0 executions.")
        elif files is not None:
            file_count = files
        else:
            # Default to 1 file
            file_count = 1

        # Get API client
        client = get_client()

        # Fetch estimate
        result = client.get_estimate(runtime=runtime, files=file_count)

        # Display header
        console.print()
        console.print(Panel.fit(
            f"[bold]Cost Estimate[/bold]\n"
            f"Runtime: {runtime}",
            border_style="cyan",
        ))
        console.print()

        # Display estimate details
        console.print(f"[bold]Estimated executions:[/bold] {result['estimated_executions']}")
        console.print(
            f"[bold]Estimated duration:[/bold] ~{result['estimated_duration_seconds']}s per execution"
        )

        # Format total duration
        total_seconds = result["estimated_total_duration_seconds"]
        if total_seconds >= 3600:
            total_hours = total_seconds / 3600
            time_display = f"{total_hours:.1f} hours"
        elif total_seconds >= 60:
            total_minutes = total_seconds / 60
            time_display = f"{total_minutes:.1f} minutes"
        else:
            time_display = f"{total_seconds} seconds"

        console.print(f"[bold]Estimated compute time:[/bold] {time_display}")
        console.print(
            f"[bold]Estimated cost:[/bold] [green]~{result['estimated_cost_display']}[/green]"
        )
        console.print()

        # Display assumptions
        console.print("[dim]Assumptions:[/dim]")
        for assumption in result["assumptions"]:
            console.print(f"  [dim]- {assumption}[/dim]")
        console.print()

        console.print("[dim]Note: Actual cost may vary based on execution time.[/dim]")
        console.print()

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()
