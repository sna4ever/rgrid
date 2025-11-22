"""Unit tests for batch progress tracking (Tier 5 - Story 5-3)."""

import pytest
from datetime import datetime, timedelta


class TestProgressCalculation:
    """Test progress calculation logic."""

    def test_progress_calculation(self):
        """Count states correctly (47/100 = 47%)."""
        # Arrange
        from cli.rgrid.batch_progress import calculate_progress

        statuses = ["completed"] * 47 + ["failed"] * 3 + ["running"] * 10 + ["queued"] * 40

        # Act
        result = calculate_progress(statuses)

        # Assert
        assert result["completed"] == 47
        assert result["failed"] == 3
        assert result["running"] == 10
        assert result["queued"] == 40
        assert result["total"] == 100
        assert result["percentage"] == 47.0

    def test_progress_calculation_empty(self):
        """Handle empty status list."""
        from cli.rgrid.batch_progress import calculate_progress

        # Act
        result = calculate_progress([])

        # Assert
        assert result["total"] == 0
        assert result["percentage"] == 0.0


class TestETACalculation:
    """Test ETA calculation logic."""

    def test_eta_calculation(self):
        """Average time × remaining jobs."""
        from cli.rgrid.batch_progress import calculate_eta

        # Arrange
        completed_count = 50
        total_count = 100
        elapsed_seconds = 300  # 5 minutes for 50 jobs = 6 seconds per job

        # Act
        eta_seconds = calculate_eta(completed_count, total_count, elapsed_seconds)

        # Assert
        # 50 remaining jobs × 6 seconds per job = 300 seconds
        assert eta_seconds == 300.0

    def test_eta_calculation_no_completions(self):
        """When no jobs completed yet, ETA should be unknown."""
        from cli.rgrid.batch_progress import calculate_eta

        # Act
        eta_seconds = calculate_eta(0, 100, 0)

        # Assert
        assert eta_seconds is None

    def test_eta_calculation_all_done(self):
        """When all jobs done, ETA should be 0."""
        from cli.rgrid.batch_progress import calculate_eta

        # Act
        eta_seconds = calculate_eta(100, 100, 600)

        # Assert
        assert eta_seconds == 0.0


class TestProgressFormatting:
    """Test progress output formatting."""

    def test_progress_formatting(self):
        """Output string formatted correctly."""
        from cli.rgrid.batch_progress import format_progress

        # Arrange
        progress = {
            "completed": 47,
            "failed": 3,
            "running": 10,
            "queued": 40,
            "total": 100,
            "percentage": 47.0
        }
        eta_seconds = 320  # 5m 20s

        # Act
        output = format_progress(progress, eta_seconds)

        # Assert
        assert "47/100" in output
        assert "47%" in output or "47.0%" in output
        assert "5m 20s" in output or "5m20s" in output
        assert "completed: 47" in output.lower() or "47" in output

    def test_progress_formatting_no_eta(self):
        """Format progress when ETA is unknown."""
        from cli.rgrid.batch_progress import format_progress

        # Arrange
        progress = {
            "completed": 0,
            "failed": 0,
            "running": 5,
            "queued": 95,
            "total": 100,
            "percentage": 0.0
        }

        # Act
        output = format_progress(progress, None)

        # Assert
        assert "0/100" in output
        assert "calculating" in output.lower() or "unknown" in output.lower() or "ETA" not in output


class TestEdgeCases:
    """Test edge case handling."""

    def test_handle_all_queued(self):
        """Edge case: no completions yet."""
        from cli.rgrid.batch_progress import calculate_progress

        # Arrange
        statuses = ["queued"] * 100

        # Act
        result = calculate_progress(statuses)

        # Assert
        assert result["completed"] == 0
        assert result["failed"] == 0
        assert result["running"] == 0
        assert result["queued"] == 100
        assert result["percentage"] == 0.0

    def test_handle_all_failed(self):
        """Edge case: 100% failure rate."""
        from cli.rgrid.batch_progress import calculate_progress

        # Arrange
        statuses = ["failed"] * 100

        # Act
        result = calculate_progress(statuses)

        # Assert
        assert result["completed"] == 0
        assert result["failed"] == 100
        assert result["running"] == 0
        assert result["queued"] == 0
        assert result["percentage"] == 0.0

    def test_handle_mixed_states(self):
        """Handle realistic mixed states."""
        from cli.rgrid.batch_progress import calculate_progress

        # Arrange
        statuses = ["completed"] * 25 + ["failed"] * 5 + ["running"] * 20 + ["queued"] * 50

        # Act
        result = calculate_progress(statuses)

        # Assert
        assert result["completed"] == 25
        assert result["failed"] == 5
        assert result["running"] == 20
        assert result["queued"] == 50
        assert result["total"] == 100


class TestTimeFormatting:
    """Test time formatting utilities."""

    def test_format_time_seconds(self):
        """Format seconds correctly."""
        from cli.rgrid.batch_progress import format_time

        assert format_time(45) == "45s"
        assert format_time(5) == "5s"

    def test_format_time_minutes(self):
        """Format minutes and seconds correctly."""
        from cli.rgrid.batch_progress import format_time

        assert format_time(320) == "5m 20s"
        assert format_time(60) == "1m 0s"
        assert format_time(125) == "2m 5s"

    def test_format_time_hours(self):
        """Format hours, minutes, and seconds correctly."""
        from cli.rgrid.batch_progress import format_time

        assert format_time(3665) == "1h 1m 5s"
        assert format_time(7200) == "2h 0m 0s"


class TestProgressBarRendering:
    """Test visual progress bar rendering."""

    def test_progress_bar_empty(self):
        """Progress bar at 0% should be empty."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(0, width=10)
        assert bar == "[          ]"

    def test_progress_bar_full(self):
        """Progress bar at 100% should be completely filled."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(100, width=10)
        assert bar == "[==========]"

    def test_progress_bar_half(self):
        """Progress bar at 50% should be half filled with arrow."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(50, width=10)
        assert bar == "[====>     ]"

    def test_progress_bar_partial(self):
        """Progress bar at 30% should show correct fill."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(30, width=10)
        assert bar == "[==>       ]"

    def test_progress_bar_negative_clamped(self):
        """Negative percentage should be clamped to 0."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(-10, width=10)
        assert bar == "[          ]"

    def test_progress_bar_over_100_clamped(self):
        """Percentage over 100 should be clamped to 100."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(150, width=10)
        assert bar == "[==========]"

    def test_progress_bar_default_width(self):
        """Default width should be 40."""
        from cli.rgrid.batch_progress import render_progress_bar

        bar = render_progress_bar(50)
        # Default width is 40, plus 2 brackets = 42 chars total
        assert len(bar) == 42
        assert bar.startswith("[")
        assert bar.endswith("]")

    def test_progress_bar_in_colored_output(self):
        """Progress bar should appear in colored output."""
        from cli.rgrid.batch_progress import format_progress_with_colors

        progress = {
            "completed": 50,
            "failed": 0,
            "running": 10,
            "queued": 40,
            "total": 100,
            "percentage": 50.0
        }

        output = format_progress_with_colors(progress, 120)
        # Should contain the progress bar characters
        assert "[" in output
        assert "]" in output
        assert ">" in output or "=" in output


class TestProgressWithCostAndDuration:
    """Test progress display with cost and duration (Story 8-5)."""

    def test_format_progress_with_cost(self):
        """Progress string should include cost when provided."""
        from cli.rgrid.batch_progress import format_progress_with_cost

        progress = {
            "completed": 50,
            "failed": 0,
            "running": 10,
            "queued": 40,
            "total": 100,
            "percentage": 50.0
        }

        # 1.5 EUR = 1_500_000 micros
        output = format_progress_with_cost(progress, eta_seconds=120, elapsed_seconds=300, cost_micros=1_500_000)

        # Should contain cost display
        assert "1.50" in output or "1.5" in output  # EUR format

    def test_format_progress_with_duration(self):
        """Progress string should include elapsed duration."""
        from cli.rgrid.batch_progress import format_progress_with_cost

        progress = {
            "completed": 50,
            "failed": 0,
            "running": 10,
            "queued": 40,
            "total": 100,
            "percentage": 50.0
        }

        output = format_progress_with_cost(progress, eta_seconds=120, elapsed_seconds=300, cost_micros=0)

        # Should contain duration (5m 0s)
        assert "5m" in output or "300s" in output or "Duration" in output

    def test_format_progress_zero_cost(self):
        """Progress should handle zero cost gracefully."""
        from cli.rgrid.batch_progress import format_progress_with_cost

        progress = {
            "completed": 10,
            "failed": 0,
            "running": 5,
            "queued": 85,
            "total": 100,
            "percentage": 10.0
        }

        output = format_progress_with_cost(progress, eta_seconds=None, elapsed_seconds=60, cost_micros=0)

        # Should not crash and should show 0 or minimal cost
        assert "0" in output or "Cost" in output

    def test_format_cost_micros_to_euros(self):
        """Test micros to euros conversion."""
        from cli.rgrid.batch_progress import format_cost

        # Test various cost amounts
        assert format_cost(0) == "0.00"
        assert format_cost(1_000_000) == "1.00"  # 1 EUR
        assert format_cost(150_000) == "0.15"  # 15 cents
        assert format_cost(12_345_678) == "12.35"  # Rounded

    def test_final_summary_with_cost(self):
        """Final summary should include total cost."""
        from cli.rgrid.batch_progress import format_final_summary_with_cost

        summary = format_final_summary_with_cost(
            succeeded=97,
            failed=3,
            elapsed_seconds=342,  # 5m 42s
            total_cost_micros=1_820_000  # EUR 1.82
        )

        assert "97" in summary
        assert "3" in summary
        assert "5m 42s" in summary or "5m42s" in summary
        assert "1.82" in summary


class TestCalculateProgressWithCost:
    """Test enhanced progress calculation with cost data."""

    def test_calculate_progress_includes_cost(self):
        """Progress calculation should work with cost data."""
        from cli.rgrid.batch_progress import calculate_progress_with_cost

        # Simulate batch status response with cost
        batch_status = {
            "statuses": ["completed"] * 50 + ["running"] * 10 + ["queued"] * 40,
            "total_cost_micros": 2_500_000  # EUR 2.50
        }

        result = calculate_progress_with_cost(batch_status)

        assert result["completed"] == 50
        assert result["total"] == 100
        assert result["cost_micros"] == 2_500_000
