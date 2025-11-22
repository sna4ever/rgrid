"""Retry a failed execution (Story 10-6).

This command allows users to retry failed or completed executions
with the same parameters (script, runtime, args, env vars, input files).
"""

import click
from rich.console import Console

from rgrid.api_client import get_client
from rgrid.errors import display_error, create_validation_error

console = Console()


@click.command()
@click.argument("execution_id")
@click.option("--force", "-f", is_flag=True, help="Retry even if not failed/completed")
def retry(execution_id: str, force: bool) -> None:
    """
    Retry a failed execution with the same parameters.

    Creates a new execution using the script, runtime, arguments,
    environment variables, and input files from the original execution.

    EXECUTION_ID: The execution ID to retry (e.g., exec_abc123)

    Examples:

        \b
        # Retry a failed execution
        $ rgrid retry exec_abc123

        \b
        # Force retry a running execution
        $ rgrid retry exec_abc123 --force
    """
    try:
        client = get_client()

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
            console.print("[dim]Only failed or completed executions can be retried by default.[/dim]")
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

        client.close()

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise click.Abort()
