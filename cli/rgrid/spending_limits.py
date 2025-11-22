"""Spending limits helper functions (Story 9-5).

Provides utility functions for parsing, calculating, and checking
spending limits for cost alerts feature.
"""

import re
from datetime import datetime
from typing import Optional

# MICRONS pattern constants (same as orchestrator/cost.py)
MICROS_PER_EURO: int = 1_000_000

# Alert thresholds
DEFAULT_WARNING_THRESHOLD_PERCENT: int = 80
BLOCKING_THRESHOLD_PERCENT: int = 100


def parse_limit_value(value: str) -> int:
    """
    Parse a spending limit value string into micros.

    Accepts various formats:
    - "50" → 50,000,000 micros (€50)
    - "50.50" → 50,500,000 micros (€50.50)
    - "€50" → 50,000,000 micros
    - "EUR50" or "EUR 50" → 50,000,000 micros
    - "€50/month" → 50,000,000 micros (AC format)
    - "0" → 0 (disabled)

    Args:
        value: String value to parse

    Returns:
        Limit value in micros

    Raises:
        ValueError: If value cannot be parsed or is negative
    """
    # Remove whitespace and convert to uppercase for prefix matching
    cleaned = value.strip()

    # Remove /month suffix (as per AC: "€50/month")
    cleaned = re.sub(r'/month$', '', cleaned, flags=re.IGNORECASE)

    # Remove currency prefixes/symbols
    cleaned = re.sub(r'^EUR\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^€', '', cleaned)

    # Remove any remaining whitespace
    cleaned = cleaned.strip()

    # Try to parse as number
    try:
        euros = float(cleaned)
    except ValueError:
        raise ValueError(f"Invalid spending limit value: '{value}'")

    if euros < 0:
        raise ValueError("Spending limit must be positive or zero")

    # Convert to micros (integer arithmetic)
    micros = int(euros * MICROS_PER_EURO)
    return micros


def format_limit_display(limit_micros: Optional[int]) -> str:
    """
    Format a spending limit in micros for human-readable display.

    Args:
        limit_micros: Limit value in micros, or None/0 for no limit

    Returns:
        Formatted string like "€50.00/month" or "No limit"
    """
    if limit_micros is None or limit_micros == 0:
        return "No limit"

    euros = limit_micros / MICROS_PER_EURO
    return f"€{euros:.2f}/month"


def calculate_limit_status(
    current_usage_micros: int,
    monthly_limit_micros: Optional[int],
) -> dict:
    """
    Calculate the current spending limit status.

    Args:
        current_usage_micros: Current month's usage in micros
        monthly_limit_micros: Monthly limit in micros (0 or None = no limit)

    Returns:
        Dictionary with:
        - status: "ok" | "warning" | "blocked" | "unlimited"
        - percent: Usage percentage (None if unlimited)
    """
    # No limit set
    if monthly_limit_micros is None or monthly_limit_micros == 0:
        return {"status": "unlimited", "percent": None}

    # Calculate percentage
    percent = (current_usage_micros * 100) // monthly_limit_micros

    # Determine status
    if percent >= BLOCKING_THRESHOLD_PERCENT:
        status = "blocked"
    elif percent >= DEFAULT_WARNING_THRESHOLD_PERCENT:
        status = "warning"
    else:
        status = "ok"

    return {"status": status, "percent": percent}


def should_trigger_alert(
    current_percent: int,
    threshold_percent: int,
    last_alert_at: Optional[datetime],
    current_month: datetime,
) -> bool:
    """
    Determine if an alert should be triggered.

    Alerts should only trigger once per month for each threshold.

    Args:
        current_percent: Current usage percentage
        threshold_percent: Threshold percentage (e.g., 80)
        last_alert_at: When alert was last triggered (None = never)
        current_month: Current date/time

    Returns:
        True if alert should be triggered
    """
    # Not at threshold yet
    if current_percent < threshold_percent:
        return False

    # Never alerted before
    if last_alert_at is None:
        return True

    # Check if alert was in a different month
    # Alert should trigger again in new month
    alert_month = (last_alert_at.year, last_alert_at.month)
    current_month_tuple = (current_month.year, current_month.month)

    return alert_month != current_month_tuple


def check_execution_allowed(
    current_usage_micros: int,
    monthly_limit_micros: Optional[int],
) -> dict:
    """
    Check if a new execution should be allowed based on spending limit.

    Args:
        current_usage_micros: Current month's usage in micros
        monthly_limit_micros: Monthly limit in micros (0 or None = no limit)

    Returns:
        Dictionary with:
        - allowed: True if execution should proceed
        - reason: Human-readable reason if blocked
    """
    # No limit set - always allow
    if monthly_limit_micros is None or monthly_limit_micros == 0:
        return {"allowed": True, "reason": ""}

    # Check if at or over limit
    if current_usage_micros >= monthly_limit_micros:
        limit_display = format_limit_display(monthly_limit_micros)
        usage_euros = current_usage_micros / MICROS_PER_EURO
        return {
            "allowed": False,
            "reason": (
                f"Monthly spending limit exceeded. "
                f"Current usage: €{usage_euros:.2f}, Limit: {limit_display}. "
                f"Increase your limit with: rgrid cost set-limit <amount>"
            ),
        }

    return {"allowed": True, "reason": ""}


def get_month_boundaries(now: datetime) -> tuple[datetime, datetime]:
    """
    Get the start and end of the current billing month.

    Args:
        now: Current date/time

    Returns:
        Tuple of (month_start, next_month_start)
    """
    # Start of current month
    month_start = datetime(now.year, now.month, 1, 0, 0, 0)

    # Start of next month
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1, 0, 0, 0)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1, 0, 0, 0)

    return month_start, next_month_start
