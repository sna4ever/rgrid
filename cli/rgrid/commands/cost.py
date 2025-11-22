"""Cost command for viewing spending breakdown (Story 9-3)."""

import click
from rich.console import Console
from rich.table import Table
from datetime import datetime, timedelta

from rgrid.api_client import get_client

console = Console()


@click.command()
@click.option(
    "--since",
    type=str,
    default=None,
    help="Start date (YYYY-MM-DD). Default: 7 days ago",
)
@click.option(
    "--until",
    type=str,
    default=None,
    help="End date (YYYY-MM-DD). Default: today",
)
def cost(since: str | None, until: str | None) -> None:
    """
    View cost breakdown by date.

    Displays daily spending including execution count, compute time,
    and cost. Defaults to last 7 days.

    Examples:

        \b
        # View costs for last 7 days (default)
        $ rgrid cost

        \b
        # View costs for specific date range
        $ rgrid cost --since 2025-11-01 --until 2025-11-15

        \b
        # View costs from start of month
        $ rgrid cost --since 2025-11-01
    """
    try:
        # Get API client
        client = get_client()

        # Fetch cost data
        result = client.get_cost(since=since, until=until)

        # Display header
        console.print(f"\n[bold]Cost Breakdown[/bold]")
        console.print(f"Period: {result['start_date']} to {result['end_date']}\n")

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Date", style="dim")
        table.add_column("Executions", justify="right")
        table.add_column("Compute Time", justify="right")
        table.add_column("Cost", justify="right", style="green")

        # Add rows for each day
        for day in result["by_date"]:
            compute_hours = day["compute_time_seconds"] / 3600
            table.add_row(
                day["date"],
                str(day["executions"]),
                f"{compute_hours:.1f}h",
                day["cost_display"],
            )

        # Only show table if there's data
        if result["by_date"]:
            console.print(table)
        else:
            console.print("[dim]No executions in this period[/dim]")

        # Display totals
        console.print()
        total_compute_seconds = sum(d["compute_time_seconds"] for d in result["by_date"])
        total_compute_hours = total_compute_seconds / 3600

        console.print(f"[bold]Total Executions:[/bold] {result['total_executions']}")
        console.print(f"[bold]Total Compute Time:[/bold] {total_compute_hours:.1f}h")
        console.print(f"[bold]Total Cost:[/bold] [green]{result['total_cost_display']}[/green]")
        console.print()

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()
