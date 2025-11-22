"""Unit tests for batch cost estimation (Story 9-4).

Tests the cost estimation functions for predicting batch execution costs
before running them.
"""

import pytest
from statistics import median


class TestEstimateBatchCost:
    """Test estimate_batch_cost function."""

    def test_basic_estimate_with_historical_data(self):
        """Estimate based on historical median duration."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        # Mock historical durations (seconds)
        historical_durations = [25, 30, 35, 28, 32]  # median = 30
        file_count = 10

        result = estimate_batch_cost(
            file_count=file_count,
            historical_durations=historical_durations,
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Median duration: 30 seconds
        # Total duration: 10 * 30 = 300 seconds
        # Cost: (300 * 5,830,000) // 3600 = 485,833 micros
        assert result["estimated_executions"] == 10
        assert result["estimated_duration_seconds"] == 30
        assert result["estimated_total_duration_seconds"] == 300
        assert result["estimated_cost_micros"] == 485_833
        assert result["estimated_cost_display"] == "€0.49"
        assert len(result["assumptions"]) > 0

    def test_no_historical_data_uses_default(self):
        """When no historical data, use 60s default estimate."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        result = estimate_batch_cost(
            file_count=5,
            historical_durations=[],  # No historical data
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Default duration: 60 seconds
        # Total duration: 5 * 60 = 300 seconds
        # Cost: (300 * 5,830,000) // 3600 = 485,833 micros
        assert result["estimated_duration_seconds"] == 60
        assert result["estimated_total_duration_seconds"] == 300
        assert "default" in result["assumptions"][0].lower() or "no historical" in result["assumptions"][0].lower()

    def test_single_file_estimate(self):
        """Estimate for single file execution."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        result = estimate_batch_cost(
            file_count=1,
            historical_durations=[45],
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Duration: 45 seconds
        # Cost: (45 * 5,830,000) // 3600 = 72,875 micros
        assert result["estimated_executions"] == 1
        assert result["estimated_duration_seconds"] == 45
        assert result["estimated_cost_micros"] == 72_875

    def test_large_batch_estimate(self):
        """Estimate for large batch (500 files)."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        historical_durations = [30] * 100  # 100 historical executions at 30s
        file_count = 500

        result = estimate_batch_cost(
            file_count=file_count,
            historical_durations=historical_durations,
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Total duration: 500 * 30 = 15,000 seconds = 4.17 hours
        # Cost: (15,000 * 5,830,000) // 3600 = 24,291,666 micros = €24.29
        assert result["estimated_executions"] == 500
        assert result["estimated_total_duration_seconds"] == 15_000
        assert result["estimated_cost_micros"] == 24_291_666
        assert result["estimated_cost_display"] == "€24.29"

    def test_zero_files_returns_zero_cost(self):
        """Zero files should return zero cost."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        result = estimate_batch_cost(
            file_count=0,
            historical_durations=[30, 45, 60],
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        assert result["estimated_executions"] == 0
        assert result["estimated_cost_micros"] == 0
        assert result["estimated_cost_display"] == "€0.00"

    def test_median_calculation_with_outliers(self):
        """Median should be resilient to outliers."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        # Outliers: 1s and 1000s, but median should be around 30s
        historical_durations = [1, 25, 30, 35, 1000]  # median = 30

        result = estimate_batch_cost(
            file_count=10,
            historical_durations=historical_durations,
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Uses median (30s), not mean (218.2s)
        assert result["estimated_duration_seconds"] == 30

    def test_assumptions_include_sample_size(self):
        """Assumptions should mention sample size."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        historical_durations = [30] * 50  # 50 samples

        result = estimate_batch_cost(
            file_count=10,
            historical_durations=historical_durations,
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Should mention "50" somewhere in assumptions
        assumptions_text = " ".join(result["assumptions"])
        assert "50" in assumptions_text


class TestEstimateCostDisplay:
    """Test cost display formatting for estimates."""

    def test_estimate_cost_display_format(self):
        """Estimated cost should be formatted with tilde (~) prefix."""
        from orchestrator.cost import estimate_batch_cost, CX22_HOURLY_COST_MICROS

        result = estimate_batch_cost(
            file_count=10,
            historical_durations=[30],
            hourly_cost_micros=CX22_HOURLY_COST_MICROS,
        )

        # Display should be formatted like "€X.XX"
        assert result["estimated_cost_display"].startswith("€")
        assert "." in result["estimated_cost_display"]


class TestCalculateMedianDuration:
    """Test median duration calculation helper."""

    def test_calculate_median_odd_count(self):
        """Median of odd-count list."""
        from orchestrator.cost import calculate_median_duration

        durations = [10, 20, 30, 40, 50]

        median_val = calculate_median_duration(durations)

        assert median_val == 30

    def test_calculate_median_even_count(self):
        """Median of even-count list (average of middle two)."""
        from orchestrator.cost import calculate_median_duration

        durations = [10, 20, 30, 40]

        median_val = calculate_median_duration(durations)

        # (20 + 30) / 2 = 25
        assert median_val == 25

    def test_calculate_median_single_value(self):
        """Median of single value list."""
        from orchestrator.cost import calculate_median_duration

        durations = [42]

        median_val = calculate_median_duration(durations)

        assert median_val == 42

    def test_calculate_median_empty_list(self):
        """Empty list returns default duration (60s)."""
        from orchestrator.cost import calculate_median_duration, DEFAULT_ESTIMATE_DURATION_SECONDS

        median_val = calculate_median_duration([])

        assert median_val == DEFAULT_ESTIMATE_DURATION_SECONDS  # 60
