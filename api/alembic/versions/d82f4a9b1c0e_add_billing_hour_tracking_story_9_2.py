"""add_billing_hour_tracking_story_9_2

Revision ID: d82f4a9b1c0e
Revises: c91e2f3a7b8d
Create Date: 2025-11-22 10:30:00.000000

Story 9-2: Implement Billing Hour Cost Amortization

Adds billing hour tracking fields to workers table:
- billing_hour_start: When the current billing hour started
- hourly_cost_micros: Worker hourly cost in micros (default CX22 = 5,830,000)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd82f4a9b1c0e'
down_revision: Union[str, Sequence[str], None] = 'f2a8c9d3b7e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Hetzner CX22 hourly cost: EUR 5.83 = 5,830,000 micros
CX22_HOURLY_COST_MICROS = 5_830_000


def upgrade() -> None:
    """Upgrade schema: Add billing hour tracking fields to workers."""
    # Add billing_hour_start column (tracks start of current billing hour)
    op.add_column(
        'workers',
        sa.Column('billing_hour_start', sa.DateTime(), nullable=True)
    )

    # Add hourly_cost_micros column (worker hourly cost in micros)
    op.add_column(
        'workers',
        sa.Column(
            'hourly_cost_micros',
            sa.BigInteger(),
            nullable=False,
            server_default=str(CX22_HOURLY_COST_MICROS)
        )
    )

    # Set billing_hour_start to created_at for existing workers
    op.execute(
        "UPDATE workers SET billing_hour_start = created_at WHERE billing_hour_start IS NULL"
    )

    # Add index for billing hour queries
    op.create_index(
        'idx_workers_billing_hour',
        'workers',
        ['billing_hour_start'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema: Remove billing hour tracking fields."""
    op.drop_index('idx_workers_billing_hour', table_name='workers')
    op.drop_column('workers', 'hourly_cost_micros')
    op.drop_column('workers', 'billing_hour_start')
