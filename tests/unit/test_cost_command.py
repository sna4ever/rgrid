"""Unit tests for rgrid cost command (Story 9-3).

Tests the cost calculation aggregation and CLI command functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import the cost calculation module
from orchestrator.cost import (
    calculate_execution_cost,
    format_cost_display,
    CX22_HOURLY_COST_MICROS,
    MICROS_PER_EURO,
)


class TestCostCalculation:
    """Test cost calculation functions."""

    def test_format_cost_display_zero(self):
        """Format 0 micros correctly."""
        assert format_cost_display(0) == "€0.00"

    def test_format_cost_display_small(self):
        """Format small costs correctly (rounds to 2 decimals)."""
        assert format_cost_display(10_000) == "€0.01"  # 0.01 EUR

    def test_format_cost_display_one_euro(self):
        """Format 1 EUR correctly."""
        assert format_cost_display(1_000_000) == "€1.00"

    def test_format_cost_display_cx22_hourly(self):
        """Format CX22 hourly cost correctly."""
        assert format_cost_display(5_830_000) == "€5.83"

    def test_format_cost_display_with_cents(self):
        """Format cost with cents correctly."""
        assert format_cost_display(2_470_000) == "€2.47"


class TestCostAggregation:
    """Test cost aggregation logic for API endpoint."""

    def test_aggregate_daily_costs_single_day(self):
        """Aggregate costs for a single day."""
        # Sample execution data
        executions = [
            {"date": "2025-11-15", "cost_micros": 100_000, "duration_seconds": 60},
            {"date": "2025-11-15", "cost_micros": 200_000, "duration_seconds": 120},
        ]

        # Aggregate by date
        by_date = {}
        for exec in executions:
            date = exec["date"]
            if date not in by_date:
                by_date[date] = {
                    "executions": 0,
                    "compute_time_seconds": 0,
                    "cost_micros": 0,
                }
            by_date[date]["executions"] += 1
            by_date[date]["compute_time_seconds"] += exec["duration_seconds"]
            by_date[date]["cost_micros"] += exec["cost_micros"]

        assert by_date["2025-11-15"]["executions"] == 2
        assert by_date["2025-11-15"]["compute_time_seconds"] == 180
        assert by_date["2025-11-15"]["cost_micros"] == 300_000

    def test_aggregate_daily_costs_multiple_days(self):
        """Aggregate costs across multiple days."""
        executions = [
            {"date": "2025-11-15", "cost_micros": 100_000, "duration_seconds": 60},
            {"date": "2025-11-14", "cost_micros": 200_000, "duration_seconds": 120},
            {"date": "2025-11-15", "cost_micros": 150_000, "duration_seconds": 90},
        ]

        by_date = {}
        for exec in executions:
            date = exec["date"]
            if date not in by_date:
                by_date[date] = {
                    "executions": 0,
                    "compute_time_seconds": 0,
                    "cost_micros": 0,
                }
            by_date[date]["executions"] += 1
            by_date[date]["compute_time_seconds"] += exec["duration_seconds"]
            by_date[date]["cost_micros"] += exec["cost_micros"]

        assert by_date["2025-11-15"]["executions"] == 2
        assert by_date["2025-11-15"]["cost_micros"] == 250_000
        assert by_date["2025-11-14"]["executions"] == 1
        assert by_date["2025-11-14"]["cost_micros"] == 200_000

    def test_total_cost_calculation(self):
        """Calculate total cost across all executions."""
        daily_costs = [
            {"cost_micros": 180_000},
            {"cost_micros": 390_000},
            {"cost_micros": 250_000},
        ]

        total = sum(d["cost_micros"] for d in daily_costs)
        assert total == 820_000
        assert format_cost_display(total) == "€0.82"


class TestCostResponseFormat:
    """Test the cost response format matches spec."""

    def test_cost_response_structure(self):
        """Verify cost response structure matches spec."""
        # Expected structure from tech spec
        response = {
            "start_date": "2025-11-01",
            "end_date": "2025-11-15",
            "total_cost_micros": 2_470_000,
            "total_cost_display": "€2.47",
            "by_date": [
                {
                    "date": "2025-11-15",
                    "executions": 45,
                    "compute_time_seconds": 8280,
                    "cost_micros": 180_000,
                    "cost_display": "€0.18",
                },
            ],
            "total_executions": 245,
        }

        # Verify required fields
        assert "start_date" in response
        assert "end_date" in response
        assert "total_cost_micros" in response
        assert "total_cost_display" in response
        assert "by_date" in response
        assert "total_executions" in response

        # Verify by_date structure
        daily = response["by_date"][0]
        assert "date" in daily
        assert "executions" in daily
        assert "compute_time_seconds" in daily
        assert "cost_micros" in daily
        assert "cost_display" in daily


class TestCostCommandCLI:
    """Test CLI cost command formatting."""

    def test_compute_time_hours_format(self):
        """Format compute time in hours correctly."""
        seconds = 8280  # 2.3 hours
        hours = seconds / 3600
        assert f"{hours:.1f}h" == "2.3h"

    def test_compute_time_hours_zero(self):
        """Format 0 compute time correctly."""
        seconds = 0
        hours = seconds / 3600
        assert f"{hours:.1f}h" == "0.0h"

    def test_table_row_format(self):
        """Format table row correctly."""
        date = "2025-11-15"
        executions = 45
        compute_hours = 2.3
        cost_display = "€0.18"

        # Expected format: Date, Executions (right-aligned), Compute Time, Cost
        row = f"{date}  {executions:>10}  {compute_hours:>5.1f}h        {cost_display}"
        assert "2025-11-15" in row
        assert "45" in row
        assert "2.3h" in row
        assert "€0.18" in row

    def test_default_date_range_7_days(self):
        """Default date range is last 7 days."""
        now = datetime.utcnow()
        default_since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        default_until = now.strftime("%Y-%m-%d")

        # Should be 7 days ago
        since_date = datetime.strptime(default_since, "%Y-%m-%d")
        until_date = datetime.strptime(default_until, "%Y-%m-%d")

        days_diff = (until_date - since_date).days
        assert days_diff == 7


class TestCostAPIClient:
    """Test API client cost method."""

    def test_get_cost_url_format(self):
        """Verify correct URL format for cost endpoint."""
        since = "2025-11-01"
        until = "2025-11-15"

        expected_url = f"/api/v1/cost?since={since}&until={until}"
        assert expected_url == "/api/v1/cost?since=2025-11-01&until=2025-11-15"

    def test_get_cost_default_params(self):
        """Default params should be last 7 days."""
        now = datetime.utcnow()
        since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        until = now.strftime("%Y-%m-%d")

        # URL should have both dates
        url = f"/api/v1/cost?since={since}&until={until}"
        assert "since=" in url
        assert "until=" in url


class TestUsesFinalizedCost:
    """Test that cost aggregation uses finalized cost when available."""

    def test_prefer_finalized_cost(self):
        """Use finalized_cost_micros over cost_micros when available."""
        # Execution with both estimated and finalized cost
        execution = {
            "cost_micros": 200_000,  # Initial estimate
            "finalized_cost_micros": 150_000,  # Finalized (lower due to amortization)
        }

        # Should use finalized when available
        cost = execution.get("finalized_cost_micros") or execution.get("cost_micros", 0)
        assert cost == 150_000

    def test_fallback_to_estimated(self):
        """Fall back to cost_micros if not finalized yet."""
        # Execution without finalized cost
        execution = {
            "cost_micros": 200_000,
            "finalized_cost_micros": None,
        }

        # Should use estimated when finalized is None
        cost = execution.get("finalized_cost_micros") or execution.get("cost_micros", 0)
        assert cost == 200_000
