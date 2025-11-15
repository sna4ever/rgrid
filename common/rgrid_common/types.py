"""
Shared type definitions for RGrid.

These types are used across CLI, API, orchestrator, and runner components.
"""

from enum import Enum


class ExecutionStatus(str, Enum):
    """
    Status of a script execution.

    Lifecycle:
        QUEUED → RUNNING → COMPLETED/FAILED
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class RuntimeType(str, Enum):
    """
    Supported runtime types for script execution.

    Each runtime corresponds to a Docker image.
    """

    PYTHON_311 = "python:3.11"
    PYTHON_310 = "python:3.10"
    PYTHON_312 = "python:3.12"

    # Future runtimes
    # NODE_20 = "node:20"
    # DENO_1 = "deno:1"

    def __str__(self) -> str:
        return self.value

    @property
    def docker_image(self) -> str:
        """Get the Docker image for this runtime."""
        return self.value


class FileType(str, Enum):
    """Types of files in the system."""

    SCRIPT = "script"
    INPUT = "input"
    OUTPUT = "output"

    def __str__(self) -> str:
        return self.value


class WorkerStatus(str, Enum):
    """Status of a worker node."""

    PROVISIONING = "provisioning"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value
