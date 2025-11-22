"""add_retry_columns_story_10_7

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-22 12:30:00.000000

Story 10-7: Auto-retry Transient Failures

Adds retry tracking columns to executions table:
- retry_count: Number of retry attempts made (default 0)
- max_retries: Maximum retry attempts allowed (default 2)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add retry tracking columns for Story 10-7."""
    # Add retry_count column (number of retry attempts made)
    op.add_column(
        'executions',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0')
    )

    # Add max_retries column (maximum retry attempts allowed)
    op.add_column(
        'executions',
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='2')
    )


def downgrade() -> None:
    """Downgrade schema: Remove retry tracking columns."""
    op.drop_column('executions', 'max_retries')
    op.drop_column('executions', 'retry_count')
