"""The user's action and resolution records for a case (ADR-031).

Revision ID: 0004_case_actions
Revises: 0003_accounts
Create Date: 2026-11-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004_case_actions'
down_revision: Union[str, None] = '0003_accounts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('kadi_case_actions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('case_id', sa.String(), nullable=False),
    sa.Column('module', sa.String(length=20), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('finding_ref', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('institution', sa.String(length=200), nullable=True),
    sa.Column('contact_method', sa.String(length=20), nullable=True),
    sa.Column('next_step', sa.String(length=500), nullable=True),
    sa.Column('amount_disputed', sa.Float(), nullable=True),
    sa.Column('amount_corrected', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['kadi_cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('kadi_case_actions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kadi_case_actions_case_id'), ['case_id'], unique=False)

    op.create_table('kadi_case_action_events',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('action_id', sa.String(), nullable=False),
    sa.Column('case_id', sa.String(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('occurred_on', sa.Date(), nullable=True),
    sa.Column('note', sa.String(length=1000), nullable=True),
    sa.Column('evidence_sha256', sa.String(length=64), nullable=True),
    sa.Column('provenance', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("provenance IN ('user_recorded')", name='ck_kadi_case_action_events_provenance'),
    sa.ForeignKeyConstraint(['action_id'], ['kadi_case_actions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['case_id'], ['kadi_cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('action_id', 'sequence', name='uq_kadi_case_action_event_sequence')
    )
    with op.batch_alter_table('kadi_case_action_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kadi_case_action_events_action_id'), ['action_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_kadi_case_action_events_case_id'), ['case_id'], unique=False)


def downgrade() -> None:
    op.drop_table('kadi_case_action_events')
    op.drop_table('kadi_case_actions')
