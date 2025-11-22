"""Unit tests for cost alerts and spending limits (Story 9-5).

Tests the spending limit functionality:
- Setting monthly spending limits via API
- 80% threshold warning alerts
- 100% threshold execution blocking
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# MICRONS pattern constants
MICROS_PER_EURO = 1_000_000


class TestSpendingLimitParser:
    """Test parsing of spending limit values from CLI."""

    def test_parse_integer_euros(self):
        """Parse plain integer as euros."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("50") == 50_000_000  # €50 in micros

    def test_parse_decimal_euros(self):
        """Parse decimal as euros."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("50.50") == 50_500_000  # €50.50 in micros

    def test_parse_euro_symbol(self):
        """Parse with euro symbol."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("€50") == 50_000_000

    def test_parse_euro_symbol_with_decimal(self):
        """Parse euro symbol with decimal."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("€50.50") == 50_500_000

    def test_parse_eur_prefix(self):
        """Parse EUR prefix."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("EUR50") == 50_000_000

    def test_parse_eur_prefix_with_space(self):
        """Parse EUR with space."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("EUR 50") == 50_000_000

    def test_parse_per_month_suffix(self):
        """Parse with /month suffix (as per AC: €50/month)."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("€50/month") == 50_000_000

    def test_parse_zero_limit(self):
        """Zero limit means disabled."""
        from rgrid.spending_limits import parse_limit_value
        assert parse_limit_value("0") == 0

    def test_parse_invalid_negative(self):
        """Negative values should raise error."""
        from rgrid.spending_limits import parse_limit_value
        with pytest.raises(ValueError, match="must be positive"):
            parse_limit_value("-50")

    def test_parse_invalid_text(self):
        """Invalid text should raise error."""
        from rgrid.spending_limits import parse_limit_value
        with pytest.raises(ValueError, match="Invalid"):
            parse_limit_value("invalid")


class TestSpendingLimitStatus:
    """Test spending limit status calculation."""

    def test_status_ok_under_threshold(self):
        """Under 80% should return 'ok' status."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=30_000_000,  # €30
            monthly_limit_micros=50_000_000,  # €50
        )
        assert status["status"] == "ok"
        assert status["percent"] == 60

    def test_status_warning_at_80_percent(self):
        """At exactly 80% should return 'warning' status."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=40_000_000,  # €40
            monthly_limit_micros=50_000_000,  # €50
        )
        assert status["status"] == "warning"
        assert status["percent"] == 80

    def test_status_warning_above_80_percent(self):
        """Above 80% but under 100% should return 'warning' status."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=45_000_000,  # €45
            monthly_limit_micros=50_000_000,  # €50
        )
        assert status["status"] == "warning"
        assert status["percent"] == 90

    def test_status_blocked_at_100_percent(self):
        """At 100% should return 'blocked' status."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=50_000_000,  # €50
            monthly_limit_micros=50_000_000,  # €50
        )
        assert status["status"] == "blocked"
        assert status["percent"] == 100

    def test_status_blocked_over_100_percent(self):
        """Over 100% should return 'blocked' status."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=60_000_000,  # €60
            monthly_limit_micros=50_000_000,  # €50
        )
        assert status["status"] == "blocked"
        assert status["percent"] == 120

    def test_status_unlimited_when_no_limit(self):
        """Zero or None limit means unlimited."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=100_000_000,  # €100
            monthly_limit_micros=0,  # No limit
        )
        assert status["status"] == "unlimited"
        assert status["percent"] is None

    def test_status_with_none_limit(self):
        """None limit means unlimited."""
        from rgrid.spending_limits import calculate_limit_status
        status = calculate_limit_status(
            current_usage_micros=100_000_000,
            monthly_limit_micros=None,
        )
        assert status["status"] == "unlimited"


class TestAlertTrigger:
    """Test alert trigger logic."""

    def test_should_trigger_80_alert_first_time(self):
        """Should trigger 80% alert when crossing threshold for first time."""
        from rgrid.spending_limits import should_trigger_alert
        result = should_trigger_alert(
            current_percent=80,
            threshold_percent=80,
            last_alert_at=None,
            current_month=datetime(2025, 11, 1),
        )
        assert result is True

    def test_should_not_trigger_80_alert_if_already_sent(self):
        """Should not re-trigger alert in same month."""
        from rgrid.spending_limits import should_trigger_alert
        result = should_trigger_alert(
            current_percent=85,
            threshold_percent=80,
            last_alert_at=datetime(2025, 11, 10),  # Already alerted this month
            current_month=datetime(2025, 11, 15),
        )
        assert result is False

    def test_should_trigger_80_alert_new_month(self):
        """Should trigger alert in new month even if sent last month."""
        from rgrid.spending_limits import should_trigger_alert
        result = should_trigger_alert(
            current_percent=80,
            threshold_percent=80,
            last_alert_at=datetime(2025, 10, 15),  # Alerted last month
            current_month=datetime(2025, 11, 15),
        )
        assert result is True

    def test_should_not_trigger_when_under_threshold(self):
        """Should not trigger when under threshold."""
        from rgrid.spending_limits import should_trigger_alert
        result = should_trigger_alert(
            current_percent=79,
            threshold_percent=80,
            last_alert_at=None,
            current_month=datetime(2025, 11, 15),
        )
        assert result is False


class TestExecutionBlockCheck:
    """Test execution blocking at 100% limit."""

    def test_should_block_at_limit(self):
        """Should block new executions when at 100% limit."""
        from rgrid.spending_limits import check_execution_allowed
        result = check_execution_allowed(
            current_usage_micros=50_000_000,  # €50
            monthly_limit_micros=50_000_000,  # €50 limit
        )
        assert result["allowed"] is False
        assert "exceeded" in result["reason"].lower()

    def test_should_block_over_limit(self):
        """Should block when over limit."""
        from rgrid.spending_limits import check_execution_allowed
        result = check_execution_allowed(
            current_usage_micros=55_000_000,  # €55
            monthly_limit_micros=50_000_000,  # €50 limit
        )
        assert result["allowed"] is False

    def test_should_allow_under_limit(self):
        """Should allow when under limit."""
        from rgrid.spending_limits import check_execution_allowed
        result = check_execution_allowed(
            current_usage_micros=45_000_000,  # €45
            monthly_limit_micros=50_000_000,  # €50 limit
        )
        assert result["allowed"] is True

    def test_should_allow_when_no_limit(self):
        """Should always allow when no limit set."""
        from rgrid.spending_limits import check_execution_allowed
        result = check_execution_allowed(
            current_usage_micros=1_000_000_000,  # €1000
            monthly_limit_micros=0,  # No limit
        )
        assert result["allowed"] is True

    def test_should_allow_when_limit_none(self):
        """Should allow when limit is None."""
        from rgrid.spending_limits import check_execution_allowed
        result = check_execution_allowed(
            current_usage_micros=1_000_000_000,
            monthly_limit_micros=None,
        )
        assert result["allowed"] is True


class TestFormatLimitDisplay:
    """Test formatting of limit values for display."""

    def test_format_limit_micros(self):
        """Format micros as euros."""
        from rgrid.spending_limits import format_limit_display
        assert format_limit_display(50_000_000) == "€50.00/month"

    def test_format_limit_with_cents(self):
        """Format with cents."""
        from rgrid.spending_limits import format_limit_display
        assert format_limit_display(50_500_000) == "€50.50/month"

    def test_format_zero_limit(self):
        """Zero displays as no limit."""
        from rgrid.spending_limits import format_limit_display
        assert format_limit_display(0) == "No limit"

    def test_format_none_limit(self):
        """None displays as no limit."""
        from rgrid.spending_limits import format_limit_display
        assert format_limit_display(None) == "No limit"


class TestGetMonthlyUsage:
    """Test monthly usage calculation."""

    def test_calculates_current_month_usage(self):
        """Calculate usage from current month start to now."""
        from rgrid.spending_limits import get_month_boundaries

        now = datetime(2025, 11, 15, 12, 30, 0)
        start, end = get_month_boundaries(now)

        assert start == datetime(2025, 11, 1, 0, 0, 0)
        assert end.month == 12 or end.day == 1  # Next month start

    def test_month_boundaries_january(self):
        """Test boundaries in January."""
        from rgrid.spending_limits import get_month_boundaries

        now = datetime(2025, 1, 15)
        start, end = get_month_boundaries(now)

        assert start == datetime(2025, 1, 1, 0, 0, 0)
        assert end.month == 2

    def test_month_boundaries_december(self):
        """Test boundaries in December."""
        from rgrid.spending_limits import get_month_boundaries

        now = datetime(2025, 12, 15)
        start, end = get_month_boundaries(now)

        assert start == datetime(2025, 12, 1, 0, 0, 0)
        assert end.year == 2026
        assert end.month == 1
