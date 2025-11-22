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

import re
import sys
from typing import Optional, Tuple
import click

# Import error types from shared package
from rgrid_common.errors import (
    RGridError,
    ValidationError,
    ExecutionError,
    RGridTimeoutError,
    NetworkError,
    AuthenticationError,
    ResourceNotFoundError,
)


def display_error(error: RGridError) -> None:
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


# Common error patterns for detection
ERROR_PATTERNS = [
    # Python import errors
    (r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", "missing_module"),
    (r"ImportError: cannot import name ['\"]([^'\"]+)['\"]", "import_error"),
    # Python syntax errors
    (r"SyntaxError: (.+)", "syntax_error"),
    (r"IndentationError: (.+)", "indentation_error"),
    # File errors
    (r"FileNotFoundError: \[Errno 2\] No such file or directory: ['\"]([^'\"]+)['\"]", "file_not_found"),
    (r"PermissionError: \[Errno 13\] Permission denied: ['\"]([^'\"]+)['\"]", "permission_denied"),
    # Memory/resource errors
    (r"MemoryError", "memory_error"),
    (r"Killed", "oom_killed"),
    # Network errors
    (r"ConnectionRefusedError", "connection_refused"),
    (r"TimeoutError|Connection timed out", "timeout"),
    # Type errors
    (r"TypeError: (.+)", "type_error"),
    (r"ValueError: (.+)", "value_error"),
    # Attribute errors
    (r"AttributeError: (.+)", "attribute_error"),
]


def detect_error_pattern(error_message: str) -> Tuple[Optional[str], Optional[str]]:
    """Detect common error patterns from an error message.

    Args:
        error_message: The error message or log output to analyze

    Returns:
        Tuple of (pattern_type, extracted_value) or (None, None) if no pattern matched
    """
    for pattern, pattern_type in ERROR_PATTERNS:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            # Extract the first capture group if present, otherwise None
            extracted = match.group(1) if match.lastindex else None
            return pattern_type, extracted
    return None, None


def create_execution_error(
    exec_id: str,
    exit_code: int,
    error_message: str,
    script_name: Optional[str] = None,
) -> ExecutionError:
    """Create a structured ExecutionError from execution failure details.

    This function analyzes the error message to detect common patterns and
    creates an ExecutionError with appropriate context and custom suggestions.

    Args:
        exec_id: The execution ID
        exit_code: The script's exit code
        error_message: The error message or log output
        script_name: Optional script filename for context

    Returns:
        ExecutionError with rich context and suggestions
    """
    context = {
        "execution_id": exec_id,
        "exit_code": exit_code,
    }
    if script_name:
        context["script"] = script_name

    # Detect specific error pattern
    pattern_type, extracted = detect_error_pattern(error_message)

    # Build message and custom suggestions based on pattern
    message = f"Script exited with code {exit_code}"
    custom_suggestions = []

    if pattern_type == "missing_module":
        module_name = extracted or "unknown"
        message = f"Missing Python module: {module_name}"
        context["missing_module"] = module_name
        custom_suggestions = [
            f"Add '{module_name}' to requirements.txt",
            "Use --runtime python:3.11-datascience for data science packages",
            "Use --runtime python:3.11-llm for AI/LLM packages",
        ]
    elif pattern_type == "import_error":
        message = f"Import error: cannot import '{extracted}'"
        context["import_name"] = extracted
        custom_suggestions = [
            "Check the import path is correct",
            "Ensure the module exports the name being imported",
        ]
    elif pattern_type == "syntax_error":
        message = f"Python syntax error: {extracted}"
        context["cause"] = "syntax_error"
        custom_suggestions = [
            "Check script for syntax errors",
            "Verify Python version compatibility",
            "Run 'python -m py_compile script.py' locally to check syntax",
        ]
    elif pattern_type == "indentation_error":
        message = f"Python indentation error: {extracted}"
        context["cause"] = "indentation_error"
        custom_suggestions = [
            "Check for mixed tabs and spaces",
            "Ensure consistent indentation throughout the file",
        ]
    elif pattern_type == "file_not_found":
        file_name = extracted or "unknown"
        message = f"File not found: {file_name}"
        context["missing_file"] = file_name
        custom_suggestions = [
            "Check the file path in your script",
            "Ensure input files are passed as arguments to rgrid run",
            "Verify file names are spelled correctly",
        ]
    elif pattern_type == "permission_denied":
        message = f"Permission denied: {extracted}"
        context["file"] = extracted
        custom_suggestions = [
            "Check file permissions",
            "Ensure the file is readable",
        ]
    elif pattern_type == "memory_error" or pattern_type == "oom_killed":
        message = "Script ran out of memory"
        context["cause"] = "out_of_memory"
        custom_suggestions = [
            "Reduce memory usage in your script",
            "Process data in smaller chunks",
            "Use generators instead of loading all data into memory",
        ]
    elif pattern_type == "timeout":
        message = "Script timed out"
        context["cause"] = "timeout"
        custom_suggestions = [
            "Increase timeout with --timeout flag",
            "Optimize script to run faster",
            "Check for infinite loops",
        ]
    elif pattern_type == "type_error":
        message = f"Type error: {extracted}"
        context["cause"] = "type_error"
        custom_suggestions = [
            "Check argument types in function calls",
            "Verify data types match expected types",
        ]
    elif pattern_type == "value_error":
        message = f"Value error: {extracted}"
        context["cause"] = "value_error"
        custom_suggestions = [
            "Check input values are valid",
            "Verify data format matches expected format",
        ]
    else:
        # Generic execution failure
        if error_message:
            # Truncate long error messages
            truncated = error_message[:200] + "..." if len(error_message) > 200 else error_message
            context["error"] = truncated

    error = ExecutionError(message, context=context)

    # Override default suggestions with custom ones if we detected a pattern
    if custom_suggestions:
        error.suggestions = custom_suggestions

    return error


def create_validation_error(
    message: str,
    file_path: Optional[str] = None,
    param: Optional[str] = None,
    value: Optional[str] = None,
) -> ValidationError:
    """Create a ValidationError for user input validation failures.

    Args:
        message: The error message
        file_path: Optional file path that failed validation
        param: Optional parameter name that was invalid
        value: Optional value that was invalid

    Returns:
        ValidationError with context
    """
    context = {}
    if file_path:
        context["file"] = file_path
    if param:
        context["parameter"] = param
    if value:
        context["value"] = value

    return ValidationError(message, context=context)


def create_network_error(
    message: str,
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None,
) -> NetworkError:
    """Create a NetworkError for API/network failures.

    Args:
        message: The error message
        endpoint: Optional API endpoint that failed
        status_code: Optional HTTP status code

    Returns:
        NetworkError with context
    """
    context = {}
    if endpoint:
        context["endpoint"] = endpoint
    if status_code:
        context["status_code"] = status_code

    return NetworkError(message, context=context)


def format_failed_execution(
    exec_id: str,
    exit_code: int,
    error_message: str,
    script_name: Optional[str] = None,
) -> None:
    """Format and display a failed execution with actionable error message.

    This is the main entry point for displaying execution failures in the CLI.
    It creates a structured error and displays it with suggestions.

    Args:
        exec_id: The execution ID
        exit_code: The script's exit code
        error_message: The error message or log output
        script_name: Optional script filename for context
    """
    error = create_execution_error(exec_id, exit_code, error_message, script_name)
    display_error(error)
    click.echo(f"View full logs: rgrid logs {exec_id}", err=True)
