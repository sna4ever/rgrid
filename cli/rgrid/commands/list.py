"""List executions with filtering (Story 10.8)."""

import click
from rich.console import Console
from rich.table import Table
from datetime import datetime

from rgrid.api_client import get_client
from rgrid.errors import display_error, create_api_error

console = Console()


@click.command("list")
@click.option("--metadata", "-m", multiple=True, help="Filter by metadata (KEY=VALUE), can be repeated")
@click.option("--status", "-s", type=click.Choice(["queued", "running", "completed", "failed"]), help="Filter by status")
@click.option("--limit", "-n", default=20, help="Maximum number of results (default: 20)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_executions(metadata: tuple[str, ...], status: str | None, limit: int, output_json: bool) -> None:
    """
    List executions with optional filtering.

    Examples:

        \b
        # List recent executions
        $ rgrid list

        \b
        # Filter by metadata
        $ rgrid list --metadata project=ml-model

        \b
        # Filter by status
        $ rgrid list --status completed

        \b
        # Combine filters
        $ rgrid list --metadata project=ml-model --status failed
    """
    # Parse metadata filters
    metadata_filter = {}
    for meta in metadata:
        if "=" not in meta:
            error = create_api_error(
                "Invalid metadata filter format",
                status_code=400,
                response_body=f"'{meta}' should be KEY=VALUE",
            )
            error.suggestions = [
                "Use format: KEY=VALUE",
                "Example: --metadata project=ml-model",
            ]
            display_error(error)
            raise click.Abort()
        key, value = meta.split("=", 1)
        metadata_filter[key] = value

    try:
        client = get_client()
        executions = client.list_executions(
            metadata_filter=metadata_filter if metadata_filter else None,
            limit=limit,
            status=status,
        )
        client.close()

        if output_json:
            import json
            console.print(json.dumps(executions, indent=2, default=str))
            return

        if not executions:
            if metadata_filter:
                filter_str = ", ".join(f"{k}={v}" for k, v in metadata_filter.items())
                console.print(f"[yellow]No executions found matching metadata: {filter_str}[/yellow]")
            elif status:
                console.print(f"[yellow]No executions found with status: {status}[/yellow]")
            else:
                console.print("[yellow]No executions found[/yellow]")
            return

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Execution ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("Duration", style="dim")
        table.add_column("Metadata", style="dim")

        for exec in executions:
            # Format status with color
            exec_status = exec.get("status", "unknown")
            if exec_status == "completed":
                status_str = "[green]completed[/green]"
            elif exec_status == "failed":
                status_str = "[red]failed[/red]"
            elif exec_status == "running":
                status_str = "[yellow]running[/yellow]"
            else:
                status_str = exec_status

            # Format created timestamp
            created_at = exec.get("created_at", "")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        dt = created_at
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_str = str(created_at)[:16]
            else:
                created_str = "-"

            # Format duration
            duration = exec.get("duration_seconds")
            if duration:
                duration_str = f"{duration}s"
            else:
                duration_str = "-"

            # Format metadata
            user_meta = exec.get("user_metadata")
            if user_meta:
                meta_str = ", ".join(f"{k}={v}" for k, v in user_meta.items())
                if len(meta_str) > 30:
                    meta_str = meta_str[:27] + "..."
            else:
                meta_str = "-"

            table.add_row(
                exec.get("execution_id", "unknown"),
                status_str,
                created_str,
                duration_str,
                meta_str,
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(executions)} execution(s)[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
