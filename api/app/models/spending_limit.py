"""Spending limit database model (Story 9-5).

Stores per-API-key monthly spending limits for cost alerts.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class SpendingLimit(Base):
    """Spending limit configuration for an API key.

    Tracks monthly spending limits and alert history for cost
    alerts feature (Story 9-5).

    Fields:
        api_key_hash: Hash of the API key (for lookup)
        monthly_limit_micros: Monthly spending limit in micros (1 EUR = 1,000,000 micros)
        alert_threshold_percent: Warning threshold (default 80%)
        is_enabled: Whether the limit is active
        last_80_alert_at: When 80% threshold alert was last triggered
        last_100_alert_at: When 100% threshold alert was last triggered
    """

    __tablename__ = "spending_limits"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Link to API key (using hash for security)
    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Limit configuration
    monthly_limit_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    alert_threshold_percent: Mapped[int] = mapped_column(Integer, default=80)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Alert tracking (when alerts were last sent in current billing period)
    last_80_alert_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_100_alert_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
