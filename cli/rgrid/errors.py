"""CLI error display formatter for RGrid (Tier 3 - Story 10-4).

This module provides user-friendly error formatting for the CLI.
Instead of raw stack traces, errors are displayed with:
- Clear error type and message
- Contextual information (file paths, IDs, etc.)
- Actionable suggestions
- Friendly formatting with emoji and colors

Example output:
    ❌ Validation Error: Script file not found

       Context:
       - file: nonexistent.py
       - location: /home/user/projects

    💡 Suggestions:
       - Check the file path is correct
       - Ensure the file exists in the current directory
"""

import sys
import click
from typing import TYPE_CHECKING

# Import error types for type hints
if TYPE_CHECKING:
    from api.errors import RGridError


def display_error(error: "RGridError") -> None:
    """Display error in friendly CLI format with emoji and context.

    Args:
        error: RGridError instance to display

    The error is formatted with:
    - Error type and message (with ❌ emoji)
    - Context information (if available)
    - Suggestions (if available, with 💡 emoji)
    """
    # Format error type name (remove "Error" suffix for cleaner display)
    error_type = error.__class__.__name__
    if error_type.endswith("Error"):
        error_type = error_type[:-5] + " Error"

    # Display error header with emoji
    click.echo(f"\n❌ {error_type}: {error.message}\n", err=True)

    # Display context if available
    if error.context:
        click.echo("   Context:", err=True)
        for key, value in error.context.items():
            # Format lists nicely
            if isinstance(value, list):
                click.echo(f"   - {key}: {', '.join(str(v) for v in value)}", err=True)
            else:
                click.echo(f"   - {key}: {value}", err=True)
        click.echo(err=True)

    # Display suggestions if available
    if hasattr(error, 'suggestions') and error.suggestions:
        click.echo("💡 Suggestions:", err=True)
        for suggestion in error.suggestions:
            click.echo(f"   - {suggestion}", err=True)
        click.echo(err=True)


def format_error_for_json(error: "RGridError") -> dict:
    """Format error as JSON for API responses.

    Args:
        error: RGridError instance to format

    Returns:
        Dictionary suitable for JSON serialization
    """
    return error.to_dict()


def handle_cli_error(error: Exception) -> None:
    """Handle any error in CLI commands.

    This is a convenience function that can be used in try/except blocks
    to handle both RGridError and generic exceptions.

    Args:
        error: Exception that was raised
    """
    # Import here to avoid circular dependency
    from api.errors import RGridError

    if isinstance(error, RGridError):
        display_error(error)
    else:
        # For non-RGrid errors, display generic error message
        click.echo(f"\n❌ Error: {str(error)}\n", err=True)
        # Show stack trace in debug mode
        if hasattr(sys, 'excepthook'):
            import traceback
            traceback.print_exc()

    sys.exit(1)
