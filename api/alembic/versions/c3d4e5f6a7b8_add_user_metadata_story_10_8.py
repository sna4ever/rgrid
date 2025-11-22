"""add_user_metadata_story_10_8

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-11-22 13:30:00.000000

Story 10-8: Execution Metadata Tagging

Adds user_metadata column to executions table:
- user_metadata: JSON field for user-provided tags (project, env, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add user_metadata column for Story 10-8."""
    # Add user_metadata JSON column for user-provided tags
    op.add_column(
        'executions',
        sa.Column('user_metadata', sa.JSON(), nullable=True)
    )

    # Create GIN index for efficient JSON queries
    op.create_index(
        'idx_executions_user_metadata',
        'executions',
        ['user_metadata'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Downgrade schema: Remove user_metadata column."""
    op.drop_index('idx_executions_user_metadata', table_name='executions')
    op.drop_column('executions', 'user_metadata')
