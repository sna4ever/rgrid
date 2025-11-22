"""add_spending_limits_table_story_9_5

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-11-22 16:00:00.000000

Story 9-5: Cost Alerts (Spending Limits)

Adds spending_limits table for per-API-key spending limits:
- api_key_hash: Hash of API key for secure lookup
- monthly_limit_micros: Monthly limit in micros (1 EUR = 1,000,000)
- alert_threshold_percent: Warning threshold (default 80%)
- is_enabled: Whether limit is active
- last_80_alert_at, last_100_alert_at: When alerts were last triggered
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add spending_limits table for Story 9-5."""
    op.create_table(
        'spending_limits',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('api_key_hash', sa.String(length=255), nullable=False),
        sa.Column('monthly_limit_micros', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('alert_threshold_percent', sa.Integer(), server_default='80', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_80_alert_at', sa.DateTime(), nullable=True),
        sa.Column('last_100_alert_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create unique index on api_key_hash for fast lookups
    op.create_index(
        op.f('ix_spending_limits_api_key_hash'),
        'spending_limits',
        ['api_key_hash'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema: Remove spending_limits table."""
    op.drop_index(op.f('ix_spending_limits_api_key_hash'), table_name='spending_limits')
    op.drop_table('spending_limits')
