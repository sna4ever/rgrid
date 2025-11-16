"""add_dependency_cache_table_for_story_6_2

Revision ID: 7bfedafb5ca5
Revises: 0266a00873cc
Create Date: 2025-11-16 11:24:14.125357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bfedafb5ca5'
down_revision: Union[str, Sequence[str], None] = '0266a00873cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add dependency_cache table for Story 6-2."""
    op.create_table(
        'dependency_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('deps_hash', sa.String(length=64), nullable=False),
        sa.Column('docker_layer_id', sa.String(length=255), nullable=False),
        sa.Column('requirements_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create unique index on deps_hash for fast lookups
    op.create_index(op.f('ix_dependency_cache_deps_hash'), 'dependency_cache', ['deps_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema: Remove dependency_cache table."""
    op.drop_index(op.f('ix_dependency_cache_deps_hash'), table_name='dependency_cache')
    op.drop_table('dependency_cache')
