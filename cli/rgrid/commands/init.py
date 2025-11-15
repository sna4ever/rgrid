"""Initialize RGrid CLI configuration."""

import secrets
import click
from rich.console import Console
from rich.prompt import Prompt

from rgrid.config import config

console = Console()


@click.command()
@click.option("--api-url", default="http://localhost:8000", help="RGrid API URL")
def init(api_url: str) -> None:
    """
    Initialize RGrid CLI configuration.

    Creates ~/.rgrid/credentials with API key.
    For walking skeleton, generates a local API key.
    """
    console.print("[bold]RGrid CLI Initialization[/bold]\n")

    if config.has_credentials():
        overwrite = Prompt.ask(
            "Credentials already exist. Overwrite?",
            choices=["y", "n"],
            default="n",
        )
        if overwrite.lower() != "y":
            console.print("[yellow]Initialization cancelled.[/yellow]")
            return

    # For walking skeleton, generate a simple API key
    # Format: sk_dev_ + 32 random hex characters
    api_key = f"sk_dev_{secrets.token_hex(16)}"

    # Save credentials
    config.save_credentials(api_key=api_key, api_url=api_url)

    console.print("\n[green]✓[/green] Configuration saved to ~/.rgrid/credentials")
    console.print(f"\n[dim]API URL:[/dim] {api_url}")
    console.print(f"[dim]API Key:[/dim] {api_key[:15]}...")
    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("\nYou can now run: [cyan]rgrid run script.py[/cyan]")
