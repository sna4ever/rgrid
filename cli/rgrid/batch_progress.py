"""Batch progress tracking and display logic (Tier 5 - Story 5-3).

Provides real-time progress updates for batch job executions with ETA calculation
and color-coded status display.
"""

import time
import sys
from typing import Dict, List, Optional, AsyncIterator
from datetime import datetime


def calculate_progress(statuses: List[str]) -> Dict:
    """Calculate progress statistics from execution statuses.

    Args:
        statuses: List of execution status strings

    Returns:
        Dictionary with completed, failed, running, queued counts, total, and percentage
    """
    if not statuses:
        return {
            "completed": 0,
            "failed": 0,
            "running": 0,
            "queued": 0,
            "total": 0,
            "percentage": 0.0
        }

    completed = len([s for s in statuses if s == "completed"])
    failed = len([s for s in statuses if s == "failed"])
    running = len([s for s in statuses if s == "running"])
    queued = len([s for s in statuses if s == "queued"])
    total = len(statuses)

    # Calculate percentage based on completed jobs only
    percentage = (completed / total * 100.0) if total > 0 else 0.0

    return {
        "completed": completed,
        "failed": failed,
        "running": running,
        "queued": queued,
        "total": total,
        "percentage": percentage
    }


def calculate_eta(completed_count: int, total_count: int, elapsed_seconds: float) -> Optional[float]:
    """Calculate estimated time to completion in seconds.

    Args:
        completed_count: Number of jobs completed so far
        total_count: Total number of jobs in batch
        elapsed_seconds: Time elapsed since batch start

    Returns:
        Estimated seconds until completion, or None if unknown
    """
    if completed_count == 0:
        return None  # No data to estimate yet

    if completed_count >= total_count:
        return 0.0  # All done

    # Calculate average time per job
    avg_time_per_job = elapsed_seconds / completed_count

    # Calculate remaining jobs
    remaining_jobs = total_count - completed_count

    # Estimate time remaining
    return avg_time_per_job * remaining_jobs


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string like "5m 20s" or "1h 2m 5s"
    """
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_progress(progress: Dict, eta_seconds: Optional[float]) -> str:
    """Format progress information as a single-line string.

    Args:
        progress: Progress dictionary from calculate_progress()
        eta_seconds: Estimated seconds to completion, or None

    Returns:
        Formatted progress string
    """
    completed = progress["completed"]
    failed = progress["failed"]
    running = progress["running"]
    queued = progress["queued"]
    total = progress["total"]
    percentage = progress["percentage"]

    # Build progress string
    progress_str = f"Progress: {completed}/{total} ({percentage:.1f}%)"

    # Add ETA if available
    if eta_seconds is not None:
        eta_str = format_time(eta_seconds)
        progress_str += f" | ETA: {eta_str}"
    else:
        progress_str += " | ETA: calculating..."

    # Add status breakdown
    progress_str += f" | Running: {running}, Queued: {queued}"

    if failed > 0:
        progress_str += f", Failed: {failed}"

    return progress_str


def format_progress_with_colors(progress: Dict, eta_seconds: Optional[float]) -> str:
    """Format progress with ANSI color codes.

    Args:
        progress: Progress dictionary from calculate_progress()
        eta_seconds: Estimated seconds to completion, or None

    Returns:
        Formatted progress string with colors
    """
    # ANSI color codes
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    completed = progress["completed"]
    failed = progress["failed"]
    running = progress["running"]
    queued = progress["queued"]
    total = progress["total"]
    percentage = progress["percentage"]

    # Build colored progress string
    progress_str = f"Progress: {completed}/{total} ({percentage:.1f}%)"

    # Add ETA if available
    if eta_seconds is not None:
        eta_str = format_time(eta_seconds)
        progress_str += f" | ETA: {eta_str}"
    else:
        progress_str += " | ETA: calculating..."

    # Add colored status breakdown
    progress_str += f" | {YELLOW}Running: {running}{RESET}, Queued: {queued}"

    if failed > 0:
        progress_str += f", {RED}Failed: {failed}{RESET}"

    if completed > 0:
        progress_str += f", {GREEN}Succeeded: {completed}{RESET}"

    return progress_str


def format_final_summary(succeeded: int, failed: int, elapsed_seconds: float) -> str:
    """Format final batch execution summary.

    Args:
        succeeded: Number of successful executions
        failed: Number of failed executions
        elapsed_seconds: Total time elapsed

    Returns:
        Formatted summary string
    """
    # ANSI color codes
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    elapsed_str = format_time(elapsed_seconds)

    summary = f"\n{GREEN}Completed:{RESET} {succeeded} succeeded"

    if failed > 0:
        summary += f", {RED}{failed} failed{RESET}"

    summary += f" (took {elapsed_str})"

    return summary


class BatchProgressTracker:
    """Async tracker for batch execution progress."""

    def __init__(self, api_client, batch_id: str, poll_interval: float = 2.0):
        """Initialize progress tracker.

        Args:
            api_client: API client instance
            batch_id: Batch ID to track
            poll_interval: Seconds between polls (default 2.0)
        """
        self.api_client = api_client
        self.batch_id = batch_id
        self.poll_interval = poll_interval
        self.start_time = None

    async def poll(self) -> AsyncIterator[Dict]:
        """Poll API for progress updates.

        Yields:
            Progress dictionaries with current status
        """
        self.start_time = time.time()

        while True:
            # Get current status from API
            response = self.api_client.get_batch_status(self.batch_id)
            statuses = response.get("statuses", [])

            # Calculate progress
            progress = calculate_progress(statuses)

            # Yield progress update
            yield progress

            # Check if all done
            if progress["completed"] + progress["failed"] >= progress["total"]:
                break

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)


def display_batch_progress(api_client, batch_id: str, poll_interval: float = 2.0):
    """Display real-time batch progress with polling.

    Args:
        api_client: API client instance
        batch_id: Batch ID to track
        poll_interval: Seconds between polls (default 2.0)
    """
    start_time = time.time()

    try:
        while True:
            # Get current status from API
            try:
                response = api_client.get_batch_status(batch_id)
                statuses = response.get("statuses", [])
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\nError polling batch status: {e}")
                time.sleep(poll_interval)
                continue

            # Calculate progress
            progress = calculate_progress(statuses)

            # Calculate ETA
            elapsed = time.time() - start_time
            eta = calculate_eta(progress["completed"], progress["total"], elapsed)

            # Format and display progress (single line, in-place update)
            progress_str = format_progress_with_colors(progress, eta)
            print(f"\r{progress_str}", end="", flush=True)

            # Check if all done
            total_finished = progress["completed"] + progress["failed"]
            if total_finished >= progress["total"]:
                # Print final summary
                elapsed_time = time.time() - start_time
                summary = format_final_summary(
                    progress["completed"],
                    progress["failed"],
                    elapsed_time
                )
                print(summary)
                break

            # Wait before next poll
            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n\nProgress monitoring interrupted. Executions continue in background.")
        print(f"Use 'rgrid status --batch {batch_id}' to check progress later.")
        # Don't re-raise - allow graceful exit


# Import asyncio if needed for async functionality
try:
    import asyncio
except ImportError:
    pass
