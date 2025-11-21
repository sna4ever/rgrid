"""add_requirements_content_story_2_4

Revision ID: 6a58dd03c588
Revises: efbe05844f15
Create Date: 2025-11-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a58dd03c588'
down_revision: Union[str, Sequence[str], None] = 'efbe05844f15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add requirements_content column for Story 2.4."""
    # Add requirements_content column to executions table
    # Stores the content of requirements.txt for auto-installing Python dependencies
    op.add_column('executions', sa.Column('requirements_content', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: Remove requirements_content column."""
    op.drop_column('executions', 'requirements_content')
