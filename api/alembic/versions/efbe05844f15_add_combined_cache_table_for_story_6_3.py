"""add_combined_cache_table_for_story_6_3

Revision ID: efbe05844f15
Revises: a078649d6ea3
Create Date: 2025-11-16 11:47:48.409759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efbe05844f15'
down_revision: Union[str, Sequence[str], None] = 'a078649d6ea3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add combined_cache table for Story 6-3."""
    op.create_table(
        'combined_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('combined_hash', sa.String(length=64), nullable=False),
        sa.Column('docker_image_tag', sa.String(length=255), nullable=False),
        sa.Column('script_content', sa.Text(), nullable=False),
        sa.Column('requirements_content', sa.Text(), nullable=False),
        sa.Column('runtime', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create unique index on combined_hash for fast lookups
    op.create_index(op.f('ix_combined_cache_combined_hash'), 'combined_cache', ['combined_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema: Remove combined_cache table."""
    op.drop_index(op.f('ix_combined_cache_combined_hash'), table_name='combined_cache')
    op.drop_table('combined_cache')
