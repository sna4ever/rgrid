"""add_execution_metadata_story_8_6

Revision ID: f2a8c9d3b7e1
Revises: c91e2f3a7b8d
Create Date: 2025-11-22 10:30:00.000000

Story 8-6: Track Execution Metadata in Database

Adds execution metadata tracking fields:
- duration_seconds: Execution duration
- worker_hostname: Worker that executed the job
- execution_metadata: JSON field for additional metadata
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a8c9d3b7e1'
down_revision: Union[str, Sequence[str], None] = 'c91e2f3a7b8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add execution metadata fields for Story 8-6."""
    # Add duration_seconds column (computed from timestamps)
    op.add_column(
        'executions',
        sa.Column('duration_seconds', sa.Integer(), nullable=True)
    )

    # Add worker_hostname column (which worker ran this job)
    op.add_column(
        'executions',
        sa.Column('worker_hostname', sa.String(128), nullable=True)
    )

    # Add execution_metadata JSON column for additional tracking data
    op.add_column(
        'executions',
        sa.Column('execution_metadata', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema: Remove execution metadata fields."""
    op.drop_column('executions', 'execution_metadata')
    op.drop_column('executions', 'worker_hostname')
    op.drop_column('executions', 'duration_seconds')
