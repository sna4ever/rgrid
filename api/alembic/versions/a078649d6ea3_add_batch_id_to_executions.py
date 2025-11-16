"""add_batch_id_to_executions

Revision ID: a078649d6ea3
Revises: 7bfedafb5ca5
Create Date: 2025-11-16 11:24:22.399020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a078649d6ea3'
down_revision: Union[str, Sequence[str], None] = '7bfedafb5ca5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add batch_id column to executions table
    op.add_column('executions', sa.Column('batch_id', sa.String(255), nullable=True))
    op.create_index('ix_executions_batch_id', 'executions', ['batch_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove batch_id column
    op.drop_index('ix_executions_batch_id', 'executions')
    op.drop_column('executions', 'batch_id')
