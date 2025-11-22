"""
MICRONS cost calculation module (Story 9-1, 9-4).

Implements the MICRONS pattern for exact precision cost tracking:
- 1 EUR = 1,000,000 micros
- All costs stored as integers (no floating point errors)
- Integer arithmetic throughout (floor division)

Cost Formula:
    cost_micros = (duration_seconds * hourly_cost_micros) // 3600

Story 9-4 additions:
- Batch cost estimation based on historical data
- Median duration calculation for estimates
"""

from typing import TypedDict

# MICRONS pattern constants
MICROS_PER_EURO: int = 1_000_000
"""1 EUR = 1,000,000 micros for sub-cent precision."""

SECONDS_PER_HOUR: int = 3600
"""Seconds in one hour."""

CX22_HOURLY_COST_MICROS: int = 5_830_000
"""Hetzner CX22 hourly cost: EUR 5.83 = 5,830,000 micros."""

DEFAULT_ESTIMATE_DURATION_SECONDS: int = 60
"""Default duration for estimates when no historical data available."""


def calculate_execution_cost(
    duration_seconds: int,
    hourly_cost_micros: int
) -> int:
    """
    Calculate execution cost in microns using integer arithmetic.

    Args:
        duration_seconds: Execution runtime in seconds (e.g., 120)
        hourly_cost_micros: Worker hourly cost in micros (e.g., 5,830,000 for CX22)

    Returns:
        Cost in microns (integer). 1 EUR = 1,000,000 micros.

    Example:
        >>> calculate_execution_cost(120, 5_830_000)
        194333  # EUR 0.194333 (120s of EUR 5.83/hr worker)

    Note:
        Uses integer floor division (//) to avoid floating point errors.
        This means costs are slightly underestimated (by < 1 micro per calc).
    """
    # Integer division (floor division) - no floats
    cost_micros = (duration_seconds * hourly_cost_micros) // SECONDS_PER_HOUR
    return cost_micros


def format_cost_display(cost_micros: int) -> str:
    """
    Format cost in microns for human-readable display.

    Args:
        cost_micros: Cost in microns (1 EUR = 1,000,000 micros)

    Returns:
        Formatted string with EUR symbol and 2 decimal places (e.g., "EUR 0.19")

    Example:
        >>> format_cost_display(194_333)
        'EUR 0.19'

        >>> format_cost_display(5_830_000)
        'EUR 5.83'
    """
    euros = cost_micros / MICROS_PER_EURO
    return f"€{euros:.2f}"


class EstimateResult(TypedDict):
    """Result type for batch cost estimation."""

    estimated_executions: int
    estimated_duration_seconds: int
    estimated_total_duration_seconds: int
    estimated_cost_micros: int
    estimated_cost_display: str
    assumptions: list[str]


def calculate_median_duration(durations: list[int]) -> int:
    """
    Calculate median duration from historical executions.

    Args:
        durations: List of execution durations in seconds

    Returns:
        Median duration (integer). Returns DEFAULT_ESTIMATE_DURATION_SECONDS
        if the list is empty.

    Example:
        >>> calculate_median_duration([10, 20, 30, 40, 50])
        30
        >>> calculate_median_duration([])
        60  # Default
    """
    if not durations:
        return DEFAULT_ESTIMATE_DURATION_SECONDS

    sorted_durations = sorted(durations)
    n = len(sorted_durations)

    if n % 2 == 1:
        # Odd number: return middle element
        return sorted_durations[n // 2]
    else:
        # Even number: return average of two middle elements (integer)
        mid = n // 2
        return (sorted_durations[mid - 1] + sorted_durations[mid]) // 2


def estimate_batch_cost(
    file_count: int,
    historical_durations: list[int],
    hourly_cost_micros: int = CX22_HOURLY_COST_MICROS,
) -> EstimateResult:
    """
    Estimate cost for a batch execution based on historical data.

    Uses median duration from historical executions to predict cost.
    This is more resilient to outliers than mean.

    Args:
        file_count: Number of files in the batch
        historical_durations: List of historical execution durations (seconds)
        hourly_cost_micros: Worker hourly cost in micros (default: CX22)

    Returns:
        EstimateResult with cost breakdown and assumptions

    Example:
        >>> result = estimate_batch_cost(10, [25, 30, 35], 5_830_000)
        >>> result["estimated_cost_display"]
        '€0.49'
    """
    # Calculate median duration
    median_duration = calculate_median_duration(historical_durations)

    # Calculate totals
    total_duration = file_count * median_duration
    estimated_cost = calculate_execution_cost(total_duration, hourly_cost_micros)

    # Build assumptions list
    assumptions: list[str] = []
    if historical_durations:
        assumptions.append(
            f"Based on {len(historical_durations)} similar executions "
            f"with median duration {median_duration}s"
        )
    else:
        assumptions.append(
            f"No historical data available, using {DEFAULT_ESTIMATE_DURATION_SECONDS}s "
            "default estimate"
        )

    return EstimateResult(
        estimated_executions=file_count,
        estimated_duration_seconds=median_duration,
        estimated_total_duration_seconds=total_duration,
        estimated_cost_micros=estimated_cost,
        estimated_cost_display=format_cost_display(estimated_cost),
        assumptions=assumptions,
    )
