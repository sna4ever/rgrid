"""Download outputs from executions on demand (Story 7-5)."""

from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from rgrid.api_client import get_client
from rgrid.utils.file_download import download_artifact_from_minio

console = Console()


@click.command()
@click.argument("execution_id")
@click.option("--output-dir", default=".", help="Directory to download files to (default: current directory)")
@click.option("--list", "list_only", is_flag=True, help="List available outputs without downloading")
@click.option("--file", "specific_file", default=None, help="Download only a specific file by name")
def download(execution_id: str, output_dir: str, list_only: bool, specific_file: str | None) -> None:
    """
    Download outputs for a previous execution.

    EXECUTION_ID: Execution or batch ID to download outputs from

    Examples:

        \b
        # Download all outputs to current directory
        $ rgrid download exec_abc123

        \b
        # Download to specific directory
        $ rgrid download exec_abc123 --output-dir ./outputs

        \b
        # List available outputs
        $ rgrid download exec_abc123 --list

        \b
        # Download specific file
        $ rgrid download exec_abc123 --file output.txt
    """
    try:
        client = get_client()

        # Get artifact list from API
        artifacts = client.get_artifacts(execution_id)

        if not artifacts:
            console.print(f"[yellow]No artifacts found for execution {execution_id}[/yellow]")
            return

        # Filter to only output artifacts
        output_artifacts = [a for a in artifacts if a.get('artifact_type') == 'output']

        if not output_artifacts:
            console.print(f"[yellow]No output artifacts found for execution {execution_id}[/yellow]")
            return

        # If --list flag is set, show table and exit
        if list_only:
            table = Table(title=f"Artifacts for {execution_id}")
            table.add_column("Filename", style="cyan")
            table.add_column("Size", justify="right")
            table.add_column("Type", style="dim")

            for artifact in output_artifacts:
                size_bytes = artifact.get('size_bytes', 0)
                size_str = _format_size(size_bytes)
                table.add_row(
                    artifact.get('filename', 'unknown'),
                    size_str,
                    artifact.get('artifact_type', 'unknown')
                )

            console.print(table)
            return

        # Filter to specific file if requested
        if specific_file:
            output_artifacts = [a for a in output_artifacts if a.get('filename') == specific_file]
            if not output_artifacts:
                console.print(f"[red]File '{specific_file}' not found in outputs[/red]")
                return

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Download each artifact
        downloaded_count = 0
        for artifact in output_artifacts:
            filename = artifact.get('filename', 'unknown')
            file_path = artifact.get('file_path')

            if not file_path:
                console.print(f"[yellow]Warning:[/yellow] No file path for {filename}")
                continue

            # Download from MinIO
            local_path = output_path / filename
            success = download_artifact_from_minio(file_path, str(local_path), client)

            if success:
                downloaded_count += 1
                console.print(f"[green]✓[/green] Downloaded: {filename}")
            else:
                console.print(f"[red]✗[/red] Failed to download: {filename}")

        console.print(f"\n[green]✓[/green] Downloaded {downloaded_count} file(s) to {output_dir}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    finally:
        client.close()


def _format_size(bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"
