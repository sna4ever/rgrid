"""Unit tests for MICRONS cost calculation (Story 9-1).

Tests the cost calculation functions following the MICRONS pattern:
- 1 EUR = 1,000,000 micros
- All costs stored as integers for exact precision
- No floating point arithmetic errors
"""

import pytest


class TestCalculateExecutionCost:
    """Test calculate_execution_cost function."""

    def test_basic_cost_calculation(self):
        """120 seconds of €5.83/hr worker = 194,333 micros."""
        from orchestrator.cost import calculate_execution_cost

        # CX22 hourly cost: €5.83 = 5,830,000 micros
        hourly_cost_micros = 5_830_000
        duration_seconds = 120

        cost = calculate_execution_cost(duration_seconds, hourly_cost_micros)

        # (120 * 5_830_000) // 3600 = 194,333
        assert cost == 194_333

    def test_zero_duration_returns_zero(self):
        """Zero duration should return zero cost."""
        from orchestrator.cost import calculate_execution_cost

        cost = calculate_execution_cost(0, 5_830_000)

        assert cost == 0

    def test_one_hour_returns_full_hourly_cost(self):
        """One full hour should return the full hourly cost."""
        from orchestrator.cost import calculate_execution_cost

        hourly_cost_micros = 5_830_000
        duration_seconds = 3600  # 1 hour

        cost = calculate_execution_cost(duration_seconds, hourly_cost_micros)

        assert cost == hourly_cost_micros

    def test_one_second_minimum_granularity(self):
        """Test cost for 1 second execution."""
        from orchestrator.cost import calculate_execution_cost

        hourly_cost_micros = 5_830_000
        duration_seconds = 1

        cost = calculate_execution_cost(duration_seconds, hourly_cost_micros)

        # (1 * 5_830_000) // 3600 = 1_619
        assert cost == 1_619

    def test_integer_arithmetic_no_float(self):
        """Verify integer division (floor) is used, not float."""
        from orchestrator.cost import calculate_execution_cost

        # Use values that would cause float rounding issues
        hourly_cost_micros = 5_830_000
        duration_seconds = 1  # Will result in fractional micros

        cost = calculate_execution_cost(duration_seconds, hourly_cost_micros)

        # Must be an integer
        assert isinstance(cost, int)
        # Floor division: 5,830,000 / 3600 = 1619.444... → 1619
        assert cost == 1619

    def test_various_durations(self):
        """Test multiple duration values."""
        from orchestrator.cost import calculate_execution_cost

        hourly_cost_micros = 5_830_000

        test_cases = [
            # (duration_seconds, expected_cost)
            (30, 48_583),    # 30 seconds
            (60, 97_166),    # 1 minute
            (300, 485_833),  # 5 minutes
            (600, 971_666),  # 10 minutes
            (1800, 2_915_000),  # 30 minutes
        ]

        for duration, expected in test_cases:
            cost = calculate_execution_cost(duration, hourly_cost_micros)
            assert cost == expected, f"Duration {duration}s: expected {expected}, got {cost}"

    def test_different_hourly_rates(self):
        """Test with different worker hourly costs."""
        from orchestrator.cost import calculate_execution_cost

        duration_seconds = 3600  # 1 hour

        # Different Hetzner instance types
        cx11_cost = 3_000_000  # €3.00/hr (hypothetical)
        cx22_cost = 5_830_000  # €5.83/hr
        cx32_cost = 10_000_000  # €10.00/hr (hypothetical)

        assert calculate_execution_cost(duration_seconds, cx11_cost) == cx11_cost
        assert calculate_execution_cost(duration_seconds, cx22_cost) == cx22_cost
        assert calculate_execution_cost(duration_seconds, cx32_cost) == cx32_cost

    def test_large_duration_no_overflow(self):
        """Test very long executions don't cause overflow."""
        from orchestrator.cost import calculate_execution_cost

        hourly_cost_micros = 5_830_000
        duration_seconds = 86400  # 24 hours

        cost = calculate_execution_cost(duration_seconds, hourly_cost_micros)

        # 24 * 5,830,000 = 139,920,000 micros = €139.92
        assert cost == 139_920_000


class TestFormatCostDisplay:
    """Test format_cost_display function."""

    def test_basic_formatting(self):
        """194,333 micros should display as €0.19."""
        from orchestrator.cost import format_cost_display

        cost_display = format_cost_display(194_333)

        assert cost_display == "€0.19"

    def test_zero_cost(self):
        """Zero cost should display as €0.00."""
        from orchestrator.cost import format_cost_display

        cost_display = format_cost_display(0)

        assert cost_display == "€0.00"

    def test_exact_euro(self):
        """1,000,000 micros should display as €1.00."""
        from orchestrator.cost import format_cost_display

        cost_display = format_cost_display(1_000_000)

        assert cost_display == "€1.00"

    def test_small_fraction(self):
        """Small costs should round to 2 decimal places."""
        from orchestrator.cost import format_cost_display

        # 1,619 micros = €0.001619 → rounds to €0.00
        cost_display = format_cost_display(1_619)

        assert cost_display == "€0.00"

    def test_larger_amounts(self):
        """Test formatting of larger amounts."""
        from orchestrator.cost import format_cost_display

        test_cases = [
            (5_830_000, "€5.83"),     # 1 hour CX22
            (10_000_000, "€10.00"),    # €10
            (100_000_000, "€100.00"),  # €100
            (500_000, "€0.50"),        # 50 cents
            (123_456_789, "€123.46"),  # Rounds correctly
        ]

        for micros, expected in test_cases:
            result = format_cost_display(micros)
            assert result == expected, f"{micros} micros: expected {expected}, got {result}"

    def test_rounding_half_cent(self):
        """Test rounding at half-cent boundary (uses Python's default rounding)."""
        from orchestrator.cost import format_cost_display

        # 155,000 micros = €0.155
        # Due to IEEE 754 float representation, 0.155 is stored as ~0.154999...
        # Python's f-string rounds this to €0.15 (banker's rounding to even)
        cost_display = format_cost_display(155_000)

        # Accept Python's standard behavior
        assert cost_display == "€0.15"

    def test_rounding_down(self):
        """Test rounding when third decimal is < 5."""
        from orchestrator.cost import format_cost_display

        # 154,000 micros = €0.154 → rounds to €0.15
        cost_display = format_cost_display(154_000)

        assert cost_display == "€0.15"


class TestMicronsConstants:
    """Test MICRONS pattern constants."""

    def test_micros_per_euro_constant(self):
        """Verify MICROS_PER_EURO constant is correct."""
        from orchestrator.cost import MICROS_PER_EURO

        assert MICROS_PER_EURO == 1_000_000

    def test_cx22_hourly_cost_constant(self):
        """Verify CX22_HOURLY_COST_MICROS constant is correct."""
        from orchestrator.cost import CX22_HOURLY_COST_MICROS

        # €5.83/hr = 5,830,000 micros
        assert CX22_HOURLY_COST_MICROS == 5_830_000

    def test_seconds_per_hour_constant(self):
        """Verify SECONDS_PER_HOUR constant is correct."""
        from orchestrator.cost import SECONDS_PER_HOUR

        assert SECONDS_PER_HOUR == 3600
