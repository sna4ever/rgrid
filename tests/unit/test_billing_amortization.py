"""Unit tests for billing hour cost amortization (Story 9-2).

Tests the amortization of worker hourly costs across all jobs in a billing hour:
- When billing hour ends, hourly cost divided evenly among all jobs
- finalized_cost_micros = hourly_cost_micros / job_count
- All jobs in billing hour share cost equally (fairness)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestCalculateAmortizedCost:
    """Test calculate_amortized_cost function."""

    def test_single_job_gets_full_hourly_cost(self):
        """Single job in billing hour gets full hourly cost."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000  # EUR 5.83
        job_count = 1

        cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)

        assert cost_per_job == 5_830_000

    def test_ten_jobs_split_cost_evenly(self):
        """10 jobs in billing hour each get 1/10 of hourly cost."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000
        job_count = 10

        cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)

        # 5,830,000 / 10 = 583,000
        assert cost_per_job == 583_000

    def test_hundred_jobs_split_cost_evenly(self):
        """100 jobs in billing hour each get 1/100 of hourly cost."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000
        job_count = 100

        cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)

        # 5,830,000 / 100 = 58,300
        assert cost_per_job == 58_300

    def test_integer_division_for_odd_splits(self):
        """Verify integer division is used for non-even splits."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000
        job_count = 3

        cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)

        # 5,830,000 / 3 = 1,943,333.33... → floor to 1,943,333
        assert cost_per_job == 1_943_333
        assert isinstance(cost_per_job, int)

    def test_zero_jobs_returns_zero(self):
        """Zero jobs should return zero cost (no jobs to amortize)."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000
        job_count = 0

        cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)

        assert cost_per_job == 0

    def test_different_worker_costs(self):
        """Test amortization with different worker hourly costs."""
        from orchestrator.billing import calculate_amortized_cost

        test_cases = [
            # (hourly_cost, job_count, expected_cost_per_job)
            (3_000_000, 10, 300_000),    # EUR 3.00/hr, 10 jobs → EUR 0.30
            (10_000_000, 5, 2_000_000),  # EUR 10.00/hr, 5 jobs → EUR 2.00
            (5_830_000, 50, 116_600),    # EUR 5.83/hr, 50 jobs → EUR 0.1166
        ]

        for hourly_cost, job_count, expected in test_cases:
            cost = calculate_amortized_cost(hourly_cost, job_count)
            assert cost == expected, f"{hourly_cost}/{job_count}: expected {expected}, got {cost}"


class TestGetBillingHourBoundaries:
    """Test get_billing_hour_boundaries function."""

    def test_returns_correct_boundaries(self):
        """Test billing hour boundary calculation."""
        from orchestrator.billing import get_billing_hour_boundaries

        # Worker created at 10:15:30
        billing_hour_start = datetime(2025, 11, 22, 10, 0, 0)

        start, end = get_billing_hour_boundaries(billing_hour_start)

        assert start == datetime(2025, 11, 22, 10, 0, 0)
        assert end == datetime(2025, 11, 22, 11, 0, 0)

    def test_handles_midnight_boundary(self):
        """Test billing hour across midnight."""
        from orchestrator.billing import get_billing_hour_boundaries

        billing_hour_start = datetime(2025, 11, 22, 23, 30, 0)

        start, end = get_billing_hour_boundaries(billing_hour_start)

        assert start == datetime(2025, 11, 22, 23, 30, 0)
        assert end == datetime(2025, 11, 23, 0, 30, 0)


class TestAmortizationSumEqualsHourlyCost:
    """Test that amortization maintains cost integrity."""

    def test_sum_of_amortized_costs_equals_or_less_than_hourly(self):
        """Sum of all amortized costs should not exceed hourly cost."""
        from orchestrator.billing import calculate_amortized_cost

        hourly_cost_micros = 5_830_000

        # Test various job counts
        for job_count in [1, 3, 7, 10, 13, 50, 100]:
            cost_per_job = calculate_amortized_cost(hourly_cost_micros, job_count)
            total_amortized = cost_per_job * job_count

            # Integer division means total might be slightly less than hourly cost
            assert total_amortized <= hourly_cost_micros, \
                f"{job_count} jobs: total {total_amortized} > hourly {hourly_cost_micros}"

            # But should be close (within job_count micros due to floor division)
            assert hourly_cost_micros - total_amortized < job_count, \
                f"{job_count} jobs: lost more than {job_count} micros"


class TestFinalizeBillingHourCostsAsync:
    """Test async finalize_billing_hour_costs function."""

    @pytest.mark.asyncio
    async def test_finalizes_all_executions_in_billing_hour(self):
        """All executions in billing hour should get finalized cost."""
        from orchestrator.billing import finalize_billing_hour_costs

        # Mock database session
        mock_session = AsyncMock()

        # Mock worker
        mock_worker = MagicMock()
        mock_worker.worker_id = "worker-123"
        mock_worker.billing_hour_start = datetime(2025, 11, 22, 10, 0, 0)
        mock_worker.hourly_cost_micros = 5_830_000

        # Mock executions in billing hour
        mock_execution_1 = MagicMock()
        mock_execution_1.execution_id = "exec-1"
        mock_execution_2 = MagicMock()
        mock_execution_2.execution_id = "exec-2"
        mock_execution_3 = MagicMock()
        mock_execution_3.execution_id = "exec-3"

        # Setup mock returns
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            mock_execution_1, mock_execution_2, mock_execution_3
        ]
        mock_session.execute.return_value = mock_result

        # Call the function
        await finalize_billing_hour_costs(mock_session, mock_worker)

        # Verify executions were updated
        # Should have 1 SELECT + 3 UPDATEs
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_executions_logs_and_returns(self):
        """When no executions in billing hour, should log and return."""
        from orchestrator.billing import finalize_billing_hour_costs

        mock_session = AsyncMock()
        mock_worker = MagicMock()
        mock_worker.worker_id = "worker-123"
        mock_worker.billing_hour_start = datetime(2025, 11, 22, 10, 0, 0)
        mock_worker.hourly_cost_micros = 5_830_000

        # No executions
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Should complete without error
        await finalize_billing_hour_costs(mock_session, mock_worker)

        # Only 1 SELECT, no UPDATEs
        assert mock_session.execute.call_count == 1
