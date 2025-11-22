"""Cost command for viewing spending breakdown and setting limits (Story 9-3, 9-5)."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

from rgrid.api_client import get_client
from rgrid.spending_limits import parse_limit_value, MICROS_PER_EURO

console = Console()


@click.group(invoke_without_command=True)
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
@click.pass_context
def cost(ctx: click.Context, since: str | None, until: str | None) -> None:
    """
    View cost breakdown and manage spending limits.

    Without subcommands, displays daily spending including execution count,
    compute time, and cost. Defaults to last 7 days.

    Subcommands:
      set-limit    Set monthly spending limit
      show-limit   Show current spending limit and status
      remove-limit Remove spending limit

    Examples:

        \b
        # View costs for last 7 days (default)
        $ rgrid cost

        \b
        # View costs for specific date range
        $ rgrid cost --since 2025-11-01 --until 2025-11-15

        \b
        # Set spending limit to €50/month
        $ rgrid cost set-limit 50
        $ rgrid cost set-limit €50/month

        \b
        # Show current limit status
        $ rgrid cost show-limit

        \b
        # Remove spending limit
        $ rgrid cost remove-limit
    """
    # If a subcommand is invoked, skip the default behavior
    if ctx.invoked_subcommand is not None:
        return

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

        # Fetch and show limit status inline
        try:
            limit_status = client.get_spending_limit()
            if limit_status.get("has_limit"):
                status_str = limit_status["status"]
                if status_str == "blocked":
                    console.print(
                        f"[bold red]Spending Limit:[/bold red] "
                        f"{limit_status['current_usage_display']} / {limit_status['monthly_limit_display']} "
                        f"([red]{limit_status['usage_percent']}% - BLOCKED[/red])"
                    )
                elif status_str == "warning":
                    console.print(
                        f"[bold yellow]Spending Limit:[/bold yellow] "
                        f"{limit_status['current_usage_display']} / {limit_status['monthly_limit_display']} "
                        f"([yellow]{limit_status['usage_percent']}%[/yellow])"
                    )
                else:
                    console.print(
                        f"[bold]Spending Limit:[/bold] "
                        f"{limit_status['current_usage_display']} / {limit_status['monthly_limit_display']} "
                        f"({limit_status['usage_percent']}%)"
                    )
                console.print()
        except Exception:
            # Don't fail if limit check fails
            pass

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cost.command("set-limit")
@click.argument("amount", type=str)
def set_limit(amount: str) -> None:
    """
    Set monthly spending limit.

    AMOUNT can be specified in various formats:
    - 50 or 50.00 (euros)
    - €50 or €50.00
    - EUR50 or EUR 50
    - €50/month (per acceptance criteria)

    At 80% usage, you will see warnings.
    At 100%, new executions will be blocked.

    Examples:

        \b
        # Set limit to €50/month
        $ rgrid cost set-limit 50
        $ rgrid cost set-limit €50/month
        $ rgrid cost set-limit EUR50
    """
    try:
        # Parse the amount
        limit_micros = parse_limit_value(amount)
        limit_euros = limit_micros / MICROS_PER_EURO

        if limit_euros == 0:
            console.print("[yellow]Setting limit to €0 will effectively disable it.[/yellow]")
            console.print("Use 'rgrid cost remove-limit' to remove limits entirely.")
            return

        # Get API client and set limit
        client = get_client()
        result = client.set_spending_limit(limit_euros)
        client.close()

        if result.get("success"):
            console.print(f"\n[green]Spending limit set successfully![/green]")
            console.print(f"[bold]Monthly Limit:[/bold] {result['monthly_limit_display']}")
            console.print(f"\n{result['message']}")
            console.print()
        else:
            console.print(f"[red]Error:[/red] {result.get('message', 'Unknown error')}")
            raise click.Abort()

    except ValueError as e:
        console.print(f"[red]Invalid amount:[/red] {str(e)}")
        console.print("Use formats like: 50, €50, EUR50, or €50/month")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cost.command("show-limit")
def show_limit() -> None:
    """
    Show current spending limit and usage status.

    Displays:
    - Current monthly limit
    - This month's usage
    - Usage percentage
    - Status (ok, warning, blocked, or unlimited)

    Example:

        $ rgrid cost show-limit
    """
    try:
        client = get_client()
        result = client.get_spending_limit()
        client.close()

        console.print("\n[bold]Spending Limit Status[/bold]\n")

        if not result.get("has_limit"):
            console.print("[dim]No spending limit configured.[/dim]")
            console.print(f"\nThis month's usage: [cyan]{result['current_usage_display']}[/cyan]")
            console.print("\nSet a limit with: [cyan]rgrid cost set-limit <amount>[/cyan]")
            console.print()
            return

        # Show limit details
        status_str = result["status"]

        # Format status with color
        if status_str == "blocked":
            status_display = "[bold red]BLOCKED[/bold red]"
        elif status_str == "warning":
            status_display = "[bold yellow]WARNING[/bold yellow]"
        else:
            status_display = "[bold green]OK[/bold green]"

        console.print(f"[bold]Monthly Limit:[/bold] {result['monthly_limit_display']}")
        console.print(f"[bold]Current Usage:[/bold] {result['current_usage_display']}")
        console.print(f"[bold]Usage:[/bold] {result['usage_percent']}%")
        console.print(f"[bold]Status:[/bold] {status_display}")
        console.print(f"[bold]Alert Threshold:[/bold] {result['alert_threshold_percent']}%")

        if result.get("message"):
            console.print(f"\n{result['message']}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cost.command("remove-limit")
def remove_limit() -> None:
    """
    Remove spending limit.

    This disables the spending limit. Usage tracking continues
    but no warnings or blocking will occur.

    Example:

        $ rgrid cost remove-limit
    """
    try:
        client = get_client()
        result = client.remove_spending_limit()
        client.close()

        if result.get("success"):
            console.print(f"\n[green]Spending limit removed.[/green]")
            console.print(f"{result.get('message', 'No usage limits enforced.')}")
            console.print()
        else:
            console.print(f"[red]Error:[/red] {result.get('message', 'Unknown error')}")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()
