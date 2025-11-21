"""add_script_cache_table_for_story_6_1

Revision ID: 50e12da834f4
Revises: 6a58dd03c588
Create Date: 2025-11-22 00:22:11.156001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50e12da834f4'
down_revision: Union[str, Sequence[str], None] = '6a58dd03c588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add script_cache table for Story 6-1.

    This table caches Docker images by script content hash,
    enabling instant execution for repeated identical scripts.
    """
    op.create_table(
        'script_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('script_hash', sa.String(length=64), nullable=False),
        sa.Column('runtime', sa.String(length=128), nullable=False),
        sa.Column('docker_image_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create unique index on (script_hash, runtime) for fast lookups
    # Same script with different runtime = different cache entry
    op.create_index(
        op.f('ix_script_cache_hash_runtime'),
        'script_cache',
        ['script_hash', 'runtime'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema: Remove script_cache table."""
    op.drop_index(op.f('ix_script_cache_hash_runtime'), table_name='script_cache')
    op.drop_table('script_cache')
