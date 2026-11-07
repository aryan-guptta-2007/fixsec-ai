"""Persist scan results and schedules, track Stripe customers

Revision ID: c4e8a1f07b2d
Revises: a362dbbfd705
Create Date: 2026-11-07 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1f07b2d'
down_revision: Union[str, Sequence[str], None] = 'a362dbbfd705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('scans', sa.Column('trigger', sa.String(), nullable=True))
    op.add_column('scans', sa.Column('branch', sa.String(), nullable=True))
    op.add_column('scans', sa.Column('security_score', sa.Float(), nullable=True))
    op.add_column('scans', sa.Column('grade', sa.String(), nullable=True))
    op.add_column('scans', sa.Column('result_json', sa.Text(), nullable=True))
    op.add_column('scans', sa.Column('error_message', sa.Text(), nullable=True))
    op.create_index('ix_scans_repo_started', 'scans', ['repo_id', 'started_at'], unique=False)

    op.create_index(
        'ix_repositories_user_repo', 'repositories', ['user_id', 'repo_name'], unique=True
    )

    op.add_column('subscriptions', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column(
        'subscriptions', sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True)
    )
    op.create_index(
        op.f('ix_subscriptions_stripe_subscription_id'),
        'subscriptions',
        ['stripe_subscription_id'],
        unique=False,
    )

    op.create_table(
        'scheduled_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('repo_name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('notification_channels', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('next_run', sa.DateTime(), nullable=False),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True),
        sa.Column('last_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scheduled_scans_id'), 'scheduled_scans', ['id'], unique=False)
    op.create_index(
        op.f('ix_scheduled_scans_next_run'), 'scheduled_scans', ['next_run'], unique=False
    )
    op.create_index(
        op.f('ix_scheduled_scans_user_id'), 'scheduled_scans', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_scheduled_scans_user_id'), table_name='scheduled_scans')
    op.drop_index(op.f('ix_scheduled_scans_next_run'), table_name='scheduled_scans')
    op.drop_index(op.f('ix_scheduled_scans_id'), table_name='scheduled_scans')
    op.drop_table('scheduled_scans')

    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    with op.batch_alter_table('subscriptions') as batch:
        batch.drop_column('cancel_at_period_end')
        batch.drop_column('stripe_customer_id')

    op.drop_index('ix_repositories_user_repo', table_name='repositories')

    op.drop_index('ix_scans_repo_started', table_name='scans')
    with op.batch_alter_table('scans') as batch:
        batch.drop_column('error_message')
        batch.drop_column('result_json')
        batch.drop_column('grade')
        batch.drop_column('security_score')
        batch.drop_column('branch')
        batch.drop_column('trigger')
