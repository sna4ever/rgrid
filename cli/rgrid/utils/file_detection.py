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
        Content of requirements.txt if found, None otherwise
    """
    script_dir = Path(script_path).parent
    requirements_path = script_dir / "requirements.txt"

    if requirements_path.exists() and requirements_path.is_file():
        try:
            return requirements_path.read_text()
        except Exception:
            return None

    return None
