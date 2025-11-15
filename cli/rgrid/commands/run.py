"""Run a Python script remotely."""

from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from rgrid.api_client import get_client
from rgrid_common.runtimes import resolve_runtime

console = Console()


@click.command()
@click.argument("script", type=click.Path(exists=True))
@click.argument("args", nargs=-1)
@click.option("--runtime", default=None, help="Runtime environment (default: python3.11)")
@click.option("--env", "-e", multiple=True, help="Environment variable (KEY=VALUE)")
def run(script: str, args: tuple[str, ...], runtime: str | None, env: tuple[str, ...]) -> None:
    """
    Run a Python script remotely.

    SCRIPT: Path to Python script to execute

    ARGS: Arguments to pass to the script

    Examples:

        \b
        # Run script with no arguments
        $ rgrid run script.py

        \b
        # Run script with arguments
        $ rgrid run process.py input.json output.json

        \b
        # Run with environment variables
        $ rgrid run script.py --env API_KEY=xxx --env DEBUG=true
    """
    script_path = Path(script)

    # Read script content
    try:
        script_content = script_path.read_text()
    except Exception as e:
        console.print(f"[red]Error reading script:[/red] {e}")
        raise click.Abort()

    # Parse environment variables
    env_vars = {}
    for env_var in env:
        if "=" not in env_var:
            console.print(f"[red]Invalid env var format:[/red] {env_var}")
            console.print("Expected format: KEY=VALUE")
            raise click.Abort()
        key, value = env_var.split("=", 1)
        env_vars[key] = value

    # Resolve runtime to Docker image
    resolved_runtime = resolve_runtime(runtime)

    # Create execution
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Submitting execution...", total=None)

            client = get_client()
            result = client.create_execution(
                script_content=script_content,
                runtime=resolved_runtime,
                args=list(args),
                env_vars=env_vars,
            )
            client.close()

        execution_id = result.get("execution_id", "unknown")
        status = result.get("status", "unknown")

        console.print(f"\n[green]✓[/green] Execution created: [cyan]{execution_id}[/cyan]")
        console.print(f"[dim]Status:[/dim] {status}")
        console.print(f"\nCheck status: [cyan]rgrid status {execution_id}[/cyan]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise click.Abort()
