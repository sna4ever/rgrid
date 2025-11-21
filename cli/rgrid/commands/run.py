"""Run a Python script remotely."""

from pathlib import Path
import click
import secrets
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from rgrid.api_client import get_client
from rgrid.utils.file_detection import detect_file_arguments, detect_requirements_file, validate_file_args
from rgrid.utils.file_upload import upload_file_to_minio, upload_file_streaming
from rgrid.batch_progress import display_batch_progress
from rgrid.batch import expand_glob_pattern, generate_batch_id
from rgrid.batch_executor import BatchExecutor
from rgrid.downloader import wait_for_completion, download_outputs
from rgrid_common.runtimes import resolve_runtime

console = Console()


@click.command()
@click.argument("script", type=click.Path(exists=True))
@click.argument("args", nargs=-1)
@click.option("--runtime", default=None, help="Runtime environment (default: python3.11)")
@click.option("--env", "-e", multiple=True, help="Environment variable (KEY=VALUE)")
@click.option("--batch", "batch_pattern", help="Glob pattern for batch execution (e.g., 'data/*.csv')")
@click.option("--parallel", default=10, help="Max concurrent executions for batch mode (default: 10)")
@click.option("--remote-only", is_flag=True, help="Skip auto-download of outputs")
def run(script: str, args: tuple[str, ...], runtime: str | None, env: tuple[str, ...], batch_pattern: str | None, parallel: int, remote_only: bool) -> None:
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

        \b
        # Run batch of scripts with multiple files
        $ rgrid run process.py --batch data/*.csv
    """
    script_path = Path(script)

    # Read script content
    try:
        script_content = script_path.read_text()
    except Exception as e:
        console.print(f"[red]Error reading script:[/red] {e}")
        raise click.Abort()

    # Story 6-2: Detect requirements.txt for dependency caching
    requirements_path = detect_requirements_file(script)
    requirements_content = None
    if requirements_path:
        # Read requirements.txt content
        try:
            requirements_content = Path(requirements_path).read_text()
            req_count = len([line for line in requirements_content.strip().split('\n') if line.strip() and not line.startswith('#')])
            console.print(f"[cyan]ℹ[/cyan] Detected requirements.txt with {req_count} dependencies")
            console.print(f"[dim]  Dependencies will be cached for faster execution[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not read requirements.txt: {e}")
            requirements_content = None

    # Parse environment variables
    env_vars = {}
    for env_var in env:
        if "=" not in env_var:
            console.print(f"[red]Invalid env var format:[/red] {env_var}")
            console.print("Expected format: KEY=VALUE")
            raise click.Abort()
        key, value = env_var.split("=", 1)
        env_vars[key] = value

    # Story 7-1: Validate file arguments exist before proceeding
    try:
        validate_file_args(list(args))
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    # Detect file arguments (Tier 4 - Story 2-5)
    file_args, regular_args = detect_file_arguments(list(args))

    # Extract just filenames for API
    input_files = [Path(file_path).name for file_path in file_args]

    # Resolve runtime to Docker image
    resolved_runtime = resolve_runtime(runtime)

    # Batch mode: Create multiple executions with same batch_id
    if batch_pattern:
        # Story 5-1: Expand glob pattern to list of files
        try:
            batch_files = expand_glob_pattern(batch_pattern)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        console.print(f"[cyan]Starting batch:[/cyan] {len(batch_files)} files (parallel: {parallel})")

        try:
            client = get_client()
            batch_id = generate_batch_id()
            executor = BatchExecutor(max_parallel=parallel)

            # Progress callback for real-time updates
            def progress_callback(completed: int, failed: int, total: int, running: int):
                console.print(
                    f"\r[{completed}/{total}] Running: {running}, "
                    f"Completed: {completed}, Failed: {failed}",
                    end=""
                )

            console.print(f"[dim]Batch ID:[/dim] {batch_id}\n")

            # Submit batch using BatchExecutor with concurrency control
            result = executor.execute_batch(
                script_content=script_content,
                files=batch_files,
                runtime=resolved_runtime,
                env_vars=env_vars,
                args=list(args),
                requirements_content=requirements_content,
                client=client,
                batch_id=batch_id,
                progress_callback=progress_callback,
            )

            console.print()  # Newline after progress
            console.print(f"\n[green]✓[/green] Batch submitted: {result.completed} succeeded, {result.failed} failed")

            # Handle output download based on --remote-only flag (Story 7-5)
            if remote_only:
                console.print(f"\n[cyan]ℹ[/cyan] Outputs stored remotely. Download with: [cyan]rgrid download {batch_id}[/cyan]")
                client.close()
            else:
                console.print(f"\nMonitoring batch progress...\n")

                # Display real-time progress (Tier 5 - Story 5-3)
                try:
                    display_batch_progress(client, batch_id, poll_interval=2.0)
                except KeyboardInterrupt:
                    # Handled in display_batch_progress
                    pass
                finally:
                    client.close()

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise click.Abort()

    # Single execution mode
    else:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(description="Submitting execution...", total=None)

                client = get_client()
                result = client.create_execution(
                    script_content=script_content,
                    runtime=resolved_runtime,
                    args=list(args),  # Keep original args for now
                    env_vars=env_vars,
                    input_files=input_files,
                    requirements_content=requirements_content,  # Story 6-2
                )

                # Upload files if any were detected (Story 7-1)
                upload_urls = result.get("upload_urls", {})
                if upload_urls:
                    progress.update(task, description=f"Uploading {len(upload_urls)} file(s)...")

                    for file_path in file_args:
                        file_path_obj = Path(file_path)
                        filename = file_path_obj.name
                        file_size = file_path_obj.stat().st_size
                        presigned_url = upload_urls.get(filename)

                        if presigned_url:
                            # Story 7-1: Show progress for large files (>1MB)
                            if file_size > 1024 * 1024:
                                progress.stop()  # Pause spinner for tqdm progress
                                console.print(f"Uploading {filename} ({file_size / (1024*1024):.1f} MB)...")
                                success = upload_file_streaming(file_path, presigned_url, show_progress=True)
                                progress.start()  # Resume spinner
                            else:
                                # Small files - use simple upload with size display
                                size_str = f"{file_size} bytes" if file_size < 1024 else f"{file_size / 1024:.1f} KB"
                                progress.update(task, description=f"Uploading {filename} ({size_str})...")
                                success = upload_file_to_minio(file_path, presigned_url)

                            if not success:
                                console.print(f"[yellow]Warning:[/yellow] Failed to upload {filename}")
                        else:
                            console.print(f"[yellow]Warning:[/yellow] No upload URL for {filename}")

                client.close()

            execution_id = result.get("execution_id", "unknown")
            status = result.get("status", "unknown")

            console.print(f"\n[green]✓[/green] Execution created: [cyan]{execution_id}[/cyan]")
            console.print(f"[dim]Status:[/dim] {status}")
            if file_args:
                console.print(f"[dim]Uploaded files:[/dim] {', '.join(input_files)}")

            # Handle output download based on --remote-only flag (Story 7-5)
            if remote_only:
                console.print(f"\n[cyan]ℹ[/cyan] Outputs stored remotely. Download with: [cyan]rgrid download {execution_id}[/cyan]")
            else:
                # Story 7-4: Auto-download outputs after completion
                console.print(f"\nWaiting for completion...")

                # Re-open client for polling (was closed after submission)
                client = get_client()
                try:
                    final_status = wait_for_completion(client, execution_id, timeout=300)

                    if final_status.get('status') == 'completed':
                        console.print(f"[green]✓[/green] Execution completed successfully")
                        download_outputs(client, execution_id)
                    else:
                        error_msg = final_status.get('error_message', 'Unknown error')
                        console.print(f"[red]✗[/red] Execution failed: {error_msg}")
                        console.print(f"\nView logs: [cyan]rgrid logs {execution_id}[/cyan]")
                except TimeoutError:
                    console.print(f"[yellow]![/yellow] Execution still running after timeout")
                    console.print(f"Check status: [cyan]rgrid status {execution_id}[/cyan]")
                finally:
                    client.close()

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise click.Abort()
