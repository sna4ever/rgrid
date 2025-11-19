"""Add metadata JSONB column to executions (Story 10-8)

Revision ID: b5c9e1234567
Revises: 0266a00873cc
Create Date: 2025-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b5c9e1234567'
down_revision: Union[str, Sequence[str], None] = '0266a00873cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add metadata JSONB column with default empty object
    op.add_column(
        'executions',
        sa.Column('metadata', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    )

    # Create GIN index for fast JSONB queries using @> operator
    # This allows efficient filtering like: WHERE metadata @> '{"key": "value"}'::jsonb
    op.create_index(
        'idx_executions_metadata',
        'executions',
        ['metadata'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove GIN index
    op.drop_index('idx_executions_metadata', 'executions')

    # Remove metadata column
    op.drop_column('executions', 'metadata')
