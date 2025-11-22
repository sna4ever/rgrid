"""add_input_cache_table_story_6_4

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-11-22 15:00:00.000000

Story 6-4: Optional Input File Caching

Adds input_cache table for caching input file references:
- input_hash: Combined SHA256 hash of all input files
- file_references: JSON dict mapping filenames to MinIO object keys
- created_at, last_used_at, use_count: Cache management fields
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add input_cache table for Story 6-4."""
    op.create_table(
        'input_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('file_references', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create unique index on input_hash for fast lookups
    op.create_index(
        op.f('ix_input_cache_input_hash'),
        'input_cache',
        ['input_hash'],
        unique=True
    )
    # Create index on last_used_at for TTL cleanup queries
    op.create_index(
        'idx_input_cache_last_used',
        'input_cache',
        ['last_used_at']
    )


def downgrade() -> None:
    """Downgrade schema: Remove input_cache table."""
    op.drop_index('idx_input_cache_last_used', table_name='input_cache')
    op.drop_index(op.f('ix_input_cache_input_hash'), table_name='input_cache')
    op.drop_table('input_cache')
