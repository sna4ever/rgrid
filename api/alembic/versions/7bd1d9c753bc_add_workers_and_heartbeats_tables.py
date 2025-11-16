"""add_workers_and_heartbeats_tables

Revision ID: 7bd1d9c753bc
Revises: ab11aed7c45a
Create Date: 2025-11-16 00:46:35.049814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bd1d9c753bc'
down_revision: Union[str, Sequence[str], None] = 'ab11aed7c45a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add workers and worker_heartbeats tables for Tier 4."""
    # Create workers table
    op.create_table(
        'workers',
        sa.Column('worker_id', sa.String(64), primary_key=True),
        sa.Column('node_id', sa.String(128), nullable=True),  # Hetzner server ID
        sa.Column('ray_node_id', sa.String(128), nullable=True),  # Ray internal node ID
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv4/IPv6 address
        sa.Column('max_concurrent', sa.Integer, default=2, nullable=False),
        sa.Column('status', sa.String(32), default='active', nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('terminated_at', sa.DateTime, nullable=True),
    )

    # Create worker_heartbeats table
    op.create_table(
        'worker_heartbeats',
        sa.Column('worker_id', sa.String(64), primary_key=True),
        sa.Column('last_heartbeat_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('ray_available_resources', sa.JSON, nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_worker_heartbeats_worker_id',
        'worker_heartbeats', 'workers',
        ['worker_id'], ['worker_id'],
        ondelete='CASCADE'
    )

    # Create index for dead worker detection queries
    op.create_index('idx_heartbeats_last', 'worker_heartbeats', ['last_heartbeat_at'])

    # Add worker tracking columns to executions table
    op.add_column('executions', sa.Column('ray_task_id', sa.String(128), nullable=True))
    op.add_column('executions', sa.Column('worker_id', sa.String(64), nullable=True))

    # Add foreign key from executions to workers
    op.create_foreign_key(
        'fk_executions_worker_id',
        'executions', 'workers',
        ['worker_id'], ['worker_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema - remove workers and worker_heartbeats tables."""
    # Drop foreign keys first
    op.drop_constraint('fk_executions_worker_id', 'executions', type_='foreignkey')
    op.drop_constraint('fk_worker_heartbeats_worker_id', 'worker_heartbeats', type_='foreignkey')

    # Drop columns from executions
    op.drop_column('executions', 'worker_id')
    op.drop_column('executions', 'ray_task_id')

    # Drop index
    op.drop_index('idx_heartbeats_last', 'worker_heartbeats')

    # Drop tables
    op.drop_table('worker_heartbeats')
    op.drop_table('workers')
