"""add_execution_logs_table_story_8_3

Revision ID: a1b2c3d4e5f6
Revises: 101cdc973ccc
Create Date: 2025-11-22 12:00:00.000000

Story 8-3: WebSocket Log Streaming

Creates execution_logs table for storing streaming log entries with:
- log_id: Unique identifier for each log entry
- execution_id: FK to executions table
- sequence_number: Monotonic counter for ordering
- timestamp: When the log was emitted
- stream: stdout or stderr
- message: Log content
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '101cdc973ccc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create execution_logs table for Story 8-3."""
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('log_id', sa.String(64), nullable=False),
        sa.Column('execution_id', sa.String(255), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('stream', sa.String(16), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.execution_id']),
    )

    # Create indexes
    op.create_index('ix_execution_logs_log_id', 'execution_logs', ['log_id'], unique=True)
    op.create_index('ix_execution_logs_execution_id', 'execution_logs', ['execution_id'])
    op.create_index('idx_execution_logs_cursor', 'execution_logs', ['execution_id', 'sequence_number'])


def downgrade() -> None:
    """Downgrade schema: Drop execution_logs table."""
    op.drop_index('idx_execution_logs_cursor', table_name='execution_logs')
    op.drop_index('ix_execution_logs_execution_id', table_name='execution_logs')
    op.drop_index('ix_execution_logs_log_id', table_name='execution_logs')
    op.drop_table('execution_logs')
