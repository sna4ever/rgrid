"""List executions with optional filtering."""

import click
from rich.console import Console
from rich.table import Table
from datetime import datetime

from rgrid.api_client import get_client

console = Console()


@click.command()
@click.option("--metadata", "-m", multiple=True, help="Filter by metadata (KEY=VALUE)")
@click.option("--limit", default=20, help="Maximum number of results (default: 20)")
def list(metadata: tuple[str, ...], limit: int) -> None:
    """
    List recent executions with optional metadata filtering.

    Examples:

        \b
        # List all recent executions
        $ rgrid list

        \b
        # Filter by metadata
        $ rgrid list --metadata project=ml-model

        \b
        # Filter by multiple metadata tags
        $ rgrid list --metadata project=ml-model --metadata env=prod

        \b
        # Show more results
        $ rgrid list --limit 50
    """
    try:
        # Parse metadata filter if provided
        metadata_dict = {}
        if metadata:
            from rgrid.utils.metadata_parser import parse_metadata, MetadataParseError

            try:
                metadata_dict = parse_metadata(list(metadata))
            except MetadataParseError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise click.Abort()

        # Fetch executions from API
        client = get_client()
        executions = client.list_executions(metadata=metadata_dict if metadata_dict else None, limit=limit)
        client.close()

        if not executions:
            if metadata_dict:
                console.print("[yellow]No executions found matching the specified metadata filter.[/yellow]")
            else:
                console.print("[yellow]No executions found.[/yellow]")
            return

        # Display results in a table
        table = Table(title=f"Recent Executions (showing {len(executions)})")
        table.add_column("Execution ID", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Runtime", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("Metadata", style="yellow")

        for execution in executions:
            execution_id = execution.get("execution_id", "")
            status = execution.get("status", "unknown")
            runtime = execution.get("runtime", "unknown")
            created_at = execution.get("created_at", "")
            metadata_obj = execution.get("metadata", {})

            # Format status with color
            status_color = {
                "queued": "blue",
                "running": "yellow",
                "completed": "green",
                "failed": "red",
            }.get(status, "white")
            status_display = f"[{status_color}]{status}[/{status_color}]"

            # Format created_at to relative time
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now(created_dt.tzinfo)
                delta = now - created_dt
                if delta.days > 0:
                    created_display = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    created_display = f"{delta.seconds // 3600}h ago"
                elif delta.seconds > 60:
                    created_display = f"{delta.seconds // 60}m ago"
                else:
                    created_display = "just now"
            except Exception:
                created_display = created_at[:19] if created_at else "unknown"

            # Format metadata
            if metadata_obj:
                metadata_display = ", ".join([f"{k}={v}" for k, v in metadata_obj.items()])
            else:
                metadata_display = "-"

            table.add_row(
                execution_id[:16] + "...",  # Truncate execution ID
                status_display,
                runtime,
                created_display,
                metadata_display
            )

        console.print(table)

        # Show filter info if metadata was used
        if metadata_dict:
            filter_str = ", ".join([f"{k}={v}" for k, v in metadata_dict.items()])
            console.print(f"\n[dim]Filtered by:[/dim] {filter_str}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
