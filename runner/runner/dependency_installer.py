"""Dependency installation for Python scripts (Story 2.4)."""

import subprocess
from pathlib import Path
from typing import Tuple


def install_dependencies(requirements_path: str) -> Tuple[bool, str]:
    """
    Install Python dependencies from requirements.txt using pip.

    Story 2.4: Auto-detect and install Python dependencies.

    Args:
        requirements_path: Path to requirements.txt file

    Returns:
        Tuple of (success: bool, logs: str)
        - success: True if installation succeeded, False otherwise
        - logs: Combined stdout and stderr from pip install
    """
    # Check if file exists
    if not Path(requirements_path).exists():
        return False, f"Requirements file not found: {requirements_path}"

    # Run pip install with requirements file
    try:
        result = subprocess.run(
            [
                "pip",
                "install",
                "-r",
                requirements_path,
                "--no-cache-dir",  # For reproducibility
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for pip install
        )

        # Combine stdout and stderr for complete logs
        logs = ""
        if result.stdout:
            logs += result.stdout
        if result.stderr:
            if logs:
                logs += "\n"
            logs += result.stderr

        # Check return code
        success = result.returncode == 0

        return success, logs if logs else "No output from pip install"

    except subprocess.TimeoutExpired:
        return False, "Pip install timeout (5 minutes exceeded)"
    except FileNotFoundError:
        return False, "Pip command not found - is Python installed?"
    except Exception as e:
        return False, f"Unexpected error during pip install: {str(e)}"
