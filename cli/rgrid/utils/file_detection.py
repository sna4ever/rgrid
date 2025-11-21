"""File argument detection for CLI."""

import os
from pathlib import Path
from typing import Tuple, List, Optional


def detect_file_arguments(args: List[str]) -> Tuple[List[str], List[str]]:
    """
    Detect which arguments are file paths vs regular arguments.

    Uses os.path.exists() to check if an argument is a file path.
    Arguments starting with '-' are treated as flags, not files.

    Args:
        args: List of command-line arguments

    Returns:
        Tuple of (file_args, regular_args)
    """
    file_args = []
    regular_args = []

    for arg in args:
        # Skip flags (arguments starting with -)
        if arg.startswith('-'):
            regular_args.append(arg)
            continue

        # Check if argument is an existing file
        if os.path.exists(arg) and os.path.isfile(arg):
            file_args.append(arg)
        else:
            regular_args.append(arg)

    return (file_args, regular_args)


def detect_requirements_file(script_path: str) -> Optional[str]:
    """
    Detect requirements.txt file in the same directory as the script.

    Args:
        script_path: Path to the script file

    Returns:
        Path to requirements.txt if found, None otherwise
    """
    script_dir = Path(script_path).parent
    requirements_path = script_dir / "requirements.txt"

    if requirements_path.exists() and requirements_path.is_file():
        return str(requirements_path)

    return None


def parse_requirements_content(content: str) -> bool:
    """
    Validate requirements.txt content format.

    Args:
        content: Content of requirements.txt file

    Returns:
        True if content is valid (including empty), False otherwise
    """
    # Empty content is valid
    if not content or content.strip() == "":
        return True

    # For now, we accept any non-empty content as valid
    # pip will handle validation during installation
    # This allows for comments, blank lines, etc.
    return True


def _looks_like_file_path(arg: str) -> bool:
    """
    Check if an argument looks like an explicit file path.

    An argument looks like a file path if:
    - Contains path separator (/ or \\)
    - Has a file extension (.csv, .json, .txt, etc.)

    Args:
        arg: Command-line argument to check

    Returns:
        True if argument looks like a file path
    """
    # Skip flags
    if arg.startswith('-'):
        return False

    # Contains path separator
    if '/' in arg or '\\' in arg:
        return True

    # Has common file extension
    common_extensions = {
        '.csv', '.json', '.txt', '.xml', '.yaml', '.yml',
        '.py', '.js', '.ts', '.html', '.css', '.md',
        '.pdf', '.png', '.jpg', '.jpeg', '.gif',
        '.zip', '.tar', '.gz', '.log', '.dat', '.bin'
    }
    path = Path(arg)
    if path.suffix.lower() in common_extensions:
        return True

    return False


def validate_file_args(args: List[str]) -> None:
    """
    Validate that explicit file path arguments exist.

    Raises FileNotFoundError if an argument looks like a file path
    but the file doesn't exist. This provides clear error messages
    when users specify files that don't exist.

    Args:
        args: List of command-line arguments

    Raises:
        FileNotFoundError: If an explicit file path doesn't exist
    """
    for arg in args:
        # Skip flags
        if arg.startswith('-'):
            continue

        # Check if this looks like an explicit file path
        if _looks_like_file_path(arg):
            # If it looks like a file path but doesn't exist, raise error
            if not os.path.exists(arg):
                raise FileNotFoundError(
                    f"File not found: {arg}\n"
                    f"Please check the path and try again."
                )
