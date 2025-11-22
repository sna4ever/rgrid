"""Retry failed executions (Story 10-6, Story 5-6).

This command allows users to retry failed or completed executions
with the same parameters (script, runtime, args, env vars, input files).

Story 5-6 adds batch retry support with --batch and --failed-only options.
"""

import click
from rich.console import Console
from rich.table import Table

from rgrid.api_client import get_client
from rgrid.errors import display_error, create_validation_error

console = Console()


@click.command()
@click.argument("execution_id", required=False)
@click.option("--batch", "-b", "batch_id", help="Retry executions from a batch")
@click.option(
    "--failed-only",
    is_flag=True,
    default=False,
    help="Only retry failed executions (use with --batch)",
)
@click.option("--force", "-f", is_flag=True, help="Retry even if not failed/completed")
def retry(
    execution_id: str | None, batch_id: str | None, failed_only: bool, force: bool
) -> None:
    """
    Retry failed execution(s) with the same parameters.

    Creates new execution(s) using the script, runtime, arguments,
    environment variables, and input files from the original execution(s).

    EXECUTION_ID: The execution ID to retry (e.g., exec_abc123)

    Examples:

        \b
        # Retry a single failed execution
        $ rgrid retry exec_abc123

        \b
        # Retry all failed executions from a batch
        $ rgrid retry --batch batch_123 --failed-only

        \b
        # Retry all executions from a batch (regardless of status)
        $ rgrid retry --batch batch_123

        \b
        # Force retry a running execution
        $ rgrid retry exec_abc123 --force
    """
    try:
        # Validate arguments
        if batch_id and execution_id:
            console.print(
                "[red]Error:[/red] Cannot specify both execution ID and --batch"
            )
            console.print("Use either [cyan]rgrid retry <execution_id>[/cyan]")
            console.print("Or [cyan]rgrid retry --batch <batch_id>[/cyan]")
            raise click.Abort()

        if not batch_id and not execution_id:
            console.print("[red]Error:[/red] Missing execution ID or --batch option")
            console.print("\nUsage:")
            console.print("  [cyan]rgrid retry <execution_id>[/cyan]")
            console.print("  [cyan]rgrid retry --batch <batch_id> --failed-only[/cyan]")
            raise click.Abort()

        client = get_client()

        if batch_id:
            # Batch retry mode (Story 5-6)
            _retry_batch(client, batch_id, failed_only)
        else:
            # Single execution retry mode (Story 10-6)
            _retry_single(client, execution_id, force)

        client.close()

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise click.Abort()


def _retry_batch(client, batch_id: str, failed_only: bool) -> None:
    """Retry executions from a batch (Story 5-6)."""
    # 1. Fetch batch executions
    try:
        executions = client.get_batch_executions(batch_id)
    except Exception as e:
        error = create_validation_error(
            f"Could not fetch batch executions: {e}",
            param="batch",
            value=batch_id,
        )
        error.suggestions = [
            "Verify the batch ID is correct",
            "Use 'rgrid status' to see recent executions",
        ]
        display_error(error)
        raise click.Abort()

    if not executions:
        console.print(f"[yellow]No executions found in batch:[/yellow] {batch_id}")
        return

    # 2. Filter by status if --failed-only
    if failed_only:
        executions_to_retry = [e for e in executions if e.get("status") == "failed"]
        filter_desc = "failed"
    else:
        executions_to_retry = executions
        filter_desc = "all"

    total_in_batch = len(executions)
    to_retry_count = len(executions_to_retry)

    if to_retry_count == 0:
        if failed_only:
            console.print(
                f"[green]No failed executions to retry in batch {batch_id}[/green]"
            )
            console.print(f"[dim]Total executions in batch: {total_in_batch}[/dim]")
        else:
            console.print(f"[yellow]No executions found in batch:[/yellow] {batch_id}")
        return

    # 3. Show what we're about to retry
    console.print(f"\n[bold]Retrying {filter_desc} executions from batch:[/bold] {batch_id}")
    console.print(f"[dim]Executions to retry: {to_retry_count}/{total_in_batch}[/dim]\n")

    # 4. Retry each execution
    retried = []
    failed_retries = []

    for exec_info in executions_to_retry:
        exec_id = exec_info.get("execution_id")
        original_status = exec_info.get("status", "unknown")

        try:
            result = client.retry_execution(exec_id)
            new_id = result.get("execution_id", "unknown")
            retried.append(
                {
                    "original_id": exec_id,
                    "new_id": new_id,
                    "original_status": original_status,
                }
            )
        except Exception as e:
            failed_retries.append(
                {"original_id": exec_id, "error": str(e), "original_status": original_status}
            )

    # 5. Display results
    if retried:
        table = Table(title="Retried Executions", show_header=True)
        table.add_column("Original ID", style="dim")
        table.add_column("New ID", style="cyan")
        table.add_column("Original Status", style="yellow")

        for r in retried:
            table.add_row(r["original_id"], r["new_id"], r["original_status"])

        console.print(table)

    if failed_retries:
        console.print(f"\n[red]Failed to retry {len(failed_retries)} execution(s):[/red]")
        for f in failed_retries:
            console.print(f"  [dim]{f['original_id']}:[/dim] {f['error']}")

    # 6. Summary
    console.print(f"\n[green]Summary:[/green]")
    console.print(f"  Batch: {batch_id}")
    console.print(f"  Successfully retried: {len(retried)}")
    if failed_retries:
        console.print(f"  [red]Failed to retry: {len(failed_retries)}[/red]")

    if retried:
        console.print(f"\nCheck status: [cyan]rgrid status <execution_id>[/cyan]")


def _retry_single(client, execution_id: str, force: bool) -> None:
    """Retry a single execution (Story 10-6)."""
    # 1. Fetch original execution to check status
    try:
        original = client.get_execution(execution_id)
    except Exception as e:
        error = create_validation_error(
            f"Could not fetch execution: {e}",
            param="execution_id",
            value=execution_id,
        )
        error.suggestions = [
            "Verify the execution ID is correct",
            "Use 'rgrid status' to list your executions",
        ]
        display_error(error)
        raise click.Abort()

    # 2. Check if retryable (unless --force)
    status = original.get("status", "unknown")
    if status not in ("failed", "completed") and not force:
        console.print(f"[yellow]Warning:[/yellow] Execution status is '{status}'")
        console.print(
            "[dim]Only failed or completed executions can be retried by default.[/dim]"
        )
        console.print("Use [cyan]--force[/cyan] to retry anyway.")
        raise click.Abort()

    # 3. Create retry execution via API
    try:
        result = client.retry_execution(execution_id)
    except Exception as e:
        console.print(f"[red]Error creating retry:[/red] {e}")
        raise click.Abort()

    new_id = result.get("execution_id", "unknown")
    new_status = result.get("status", "queued")

    # 4. Display success message
    console.print(f"\n[green]Retry started:[/green] [cyan]{new_id}[/cyan]")
    console.print(f"[dim]Original:[/dim] {execution_id}")
    console.print(f"[dim]Status:[/dim] {new_status}")

    # Show original error if available
    original_error = original.get("error_message") or original.get("execution_error")
    if original_error:
        console.print(f"\n[dim]Original error:[/dim]")
        # Truncate long errors
        if len(original_error) > 200:
            original_error = original_error[:200] + "..."
        console.print(f"[dim]{original_error}[/dim]")

    console.print(f"\nCheck status: [cyan]rgrid status {new_id}[/cyan]")
    console.print(f"View logs: [cyan]rgrid logs {new_id}[/cyan]")
