"""kadi_document_jobs: persisted document processing state (ADR-019).

Revision ID: 0002_document_jobs
Revises: 0001_baseline
Create Date: 2026-10-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002_document_jobs'
down_revision: Union[str, None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('kadi_document_jobs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('case_id', sa.String(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('pipeline_version', sa.String(), nullable=False),
    sa.Column('error_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("state IN ('queued', 'processing', 'completed', 'duplicate', 'failed', 'interrupted')", name='ck_kadi_document_jobs_state'),
    sa.ForeignKeyConstraint(['case_id'], ['kadi_cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('kadi_document_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kadi_document_jobs_case_id'), ['case_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('kadi_document_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_kadi_document_jobs_case_id'))

    op.drop_table('kadi_document_jobs')
