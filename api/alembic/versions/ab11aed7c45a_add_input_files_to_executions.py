"""add_input_files_to_executions

Revision ID: ab11aed7c45a
Revises: fc0e7b400c13
Create Date: 2025-11-16 00:31:24.344972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab11aed7c45a'
down_revision: Union[str, Sequence[str], None] = 'fc0e7b400c13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add input_files column for Tier 4 file handling."""
    # Add input_files JSON column (default to empty list)
    op.add_column('executions', sa.Column('input_files', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema - remove input_files column."""
    op.drop_column('executions', 'input_files')
