"""add_cost_tracking_fields_story_9_1

Revision ID: c91e2f3a7b8d
Revises: 6a58dd03c588
Create Date: 2025-11-22 00:40:00.000000

Story 9-1: Implement MICRONS Cost Calculation

Adds finalized cost fields for billing hour amortization:
- finalized_cost_micros: Final cost after billing hour ends
- cost_finalized_at: Timestamp when cost was finalized
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c91e2f3a7b8d'
down_revision: Union[str, Sequence[str], None] = '6a58dd03c588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add cost tracking fields for Story 9-1."""
    # Add finalized_cost_micros column (nullable until billing hour ends)
    op.add_column(
        'executions',
        sa.Column('finalized_cost_micros', sa.BigInteger(), nullable=True)
    )

    # Add cost_finalized_at timestamp (when billing hour cost was finalized)
    op.add_column(
        'executions',
        sa.Column('cost_finalized_at', sa.DateTime(), nullable=True)
    )

    # Add index for cost queries (used by rgrid cost command)
    op.create_index(
        'idx_executions_cost_date',
        'executions',
        ['created_at', 'cost_micros'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema: Remove cost tracking fields."""
    op.drop_index('idx_executions_cost_date', table_name='executions')
    op.drop_column('executions', 'cost_finalized_at')
    op.drop_column('executions', 'finalized_cost_micros')
