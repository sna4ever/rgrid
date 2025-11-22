"""merge_story_branches

Revision ID: 101cdc973ccc
Revises: 50e12da834f4, d82f4a9b1c0e
Create Date: 2025-11-22 11:55:03.997061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '101cdc973ccc'
down_revision: Union[str, Sequence[str], None] = ('50e12da834f4', 'd82f4a9b1c0e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
