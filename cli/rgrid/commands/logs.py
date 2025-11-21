"""Logs command for viewing execution output (Story 8.2 + 8.3)."""

import asyncio
import json
import signal
import sys
from typing import Optional

import click
from rich.console import Console

from rgrid.api_client import get_client
from rgrid.config import get_settings

console = Console()


def process_websocket_message(message: str) -> dict:
    """
    Process a WebSocket message and return parsed result.

    Args:
        message: JSON-encoded WebSocket message

    Returns:
        Dictionary with type, content, and continue flag
    """
    data = json.loads(message)
    msg_type = data.get("type", "unknown")

    if msg_type == "log":
        return {
            "type": "log",
            "sequence_number": data.get("sequence_number"),
            "timestamp": data.get("timestamp"),
            "stream": data.get("stream"),
            "message": data.get("message"),
            "continue": True,
        }
    elif msg_type == "complete":
        return {
            "type": "complete",
            "exit_code": data.get("exit_code"),
            "status": data.get("status"),
            "continue": False,
        }
    elif msg_type == "error":
        return {
            "type": "error",
            "error": data.get("error"),
            "continue": False,
        }
    else:
        return {
            "type": "unknown",
            "data": data,
            "continue": True,
        }


def format_log_line(stream: str, message: str, timestamp: Optional[str] = None) -> str:
    """Format a log line for display."""
    if stream == "stderr":
        return f"[red]{message}[/red]"
    return message


async def _stream_logs_websocket(execution_id: str) -> None:
    """
    Stream logs in real-time via WebSocket.

    Args:
        execution_id: Execution ID to stream logs for
    """
    import websockets

    settings = get_settings()
    api_url = settings.api_url

    # Convert HTTP URL to WebSocket URL
    ws_url = api_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = ws_url.rstrip("/")

    # WebSocket endpoint
    endpoint = f"{ws_url}/ws/executions/{execution_id}/logs"

    last_sequence = -1
    reconnect_delay = 1
    max_reconnect_delay = 30

    # Handle Ctrl+C gracefully
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        console.print("\n[yellow]Disconnecting from log stream...[/yellow]")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    console.print(f"[cyan]Connecting to log stream for {execution_id}...[/cyan]")

    while not stop_event.is_set():
        try:
            async with websockets.connect(
                f"{endpoint}?cursor={last_sequence}",
                ping_interval=20,
                ping_timeout=20,
            ) as websocket:
                console.print("[green]Connected to log stream[/green]")
                reconnect_delay = 1  # Reset on successful connection

                async for message in websocket:
                    if stop_event.is_set():
                        break

                    result = process_websocket_message(message)

                    if result["type"] == "log":
                        # Display log line
                        output = format_log_line(
                            result["stream"],
                            result["message"],
                            result.get("timestamp"),
                        )
                        console.print(output)
                        last_sequence = result["sequence_number"]

                    elif result["type"] == "complete":
                        exit_code = result["exit_code"]
                        if exit_code == 0:
                            console.print(
                                f"\n[green]Execution completed (exit code: {exit_code})[/green]"
                            )
                        else:
                            console.print(
                                f"\n[red]Execution failed (exit code: {exit_code})[/red]"
                            )
                        return

                    elif result["type"] == "error":
                        console.print(f"\n[red]Error: {result['error']}[/red]")
                        return

                    if not result["continue"]:
                        return

        except websockets.ConnectionClosed:
            if stop_event.is_set():
                return
            console.print(
                f"[yellow]Connection lost. Reconnecting in {reconnect_delay}s...[/yellow]"
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

        except Exception as e:
            if stop_event.is_set():
                return
            console.print(f"[red]WebSocket error: {e}[/red]")
            console.print(
                f"[yellow]Reconnecting in {reconnect_delay}s...[/yellow]"
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def stream_logs_websocket(execution_id: str) -> None:
    """
    Stream logs via WebSocket (sync wrapper).

    Args:
        execution_id: Execution ID to stream logs for
    """
    try:
        asyncio.run(_stream_logs_websocket(execution_id))
    except KeyboardInterrupt:
        console.print("\n[yellow]Disconnected from log stream[/yellow]")


@click.command()
@click.argument("execution_id")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Stream logs in real-time via WebSocket",
)
@click.option(
    "--stdout-only",
    is_flag=True,
    help="Show only stdout",
)
@click.option(
    "--stderr-only",
    is_flag=True,
    help="Show only stderr",
)
def logs(
    execution_id: str,
    follow: bool,
    stdout_only: bool,
    stderr_only: bool,
) -> None:
    """
    View execution logs (stdout/stderr).

    Args:
        execution_id: Execution ID to view logs for
        follow: Stream logs in real-time
        stdout_only: Show only stdout
        stderr_only: Show only stderr
    """
    # Real-time streaming mode
    if follow:
        stream_logs_websocket(execution_id)
        return

    # Historical logs mode (existing behavior)
    try:
        # Get API client
        client = get_client()

        # Fetch execution
        result = client.get_execution(execution_id)

        # Check if execution has output
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        output_truncated = result.get("output_truncated", False)

        if not stdout and not stderr:
            console.print("[yellow]No output available for this execution[/yellow]")
            return

        # Display stdout
        if stdout and not stderr_only:
            if stdout_only or stderr:
                console.print("\n[bold cyan]STDOUT:[/bold cyan]")
            console.print(stdout.rstrip())

        # Display stderr
        if stderr and not stdout_only:
            if stderr_only or stdout:
                console.print("\n[bold red]STDERR:[/bold red]")
            console.print(f"[red]{stderr.rstrip()}[/red]")

        # Show truncation warning
        if output_truncated:
            console.print(
                "\n[yellow]Output was truncated (exceeded 100KB limit)[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()
