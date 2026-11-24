"""User accounts, sessions, account tokens, case ownership and owned BimaNyay records (ADR-026).

Revision ID: 0003_accounts
Revises: 0002_document_jobs
Create Date: 2026-11-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003_accounts'
down_revision: Union[str, None] = '0002_document_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('kadi_users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('email_verified_at', sa.DateTime(), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('kadi_sessions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('transport', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("transport IN ('cookie', 'bearer')", name='ck_kadi_sessions_transport'),
    sa.ForeignKeyConstraint(['user_id'], ['kadi_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    with op.batch_alter_table('kadi_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kadi_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('kadi_account_tokens',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('purpose', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("purpose IN ('verify_email', 'reset_password')", name='ck_kadi_account_tokens_purpose'),
    sa.ForeignKeyConstraint(['user_id'], ['kadi_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    with op.batch_alter_table('kadi_account_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kadi_account_tokens_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('kadi_cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_user_id', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_kadi_cases_owner_user_id'), ['owner_user_id'], unique=False)
        batch_op.create_foreign_key('fk_kadi_cases_owner_user_id_kadi_users', 'kadi_users', ['owner_user_id'], ['id'])

    for table in ('bimanyay_cases', 'bimanyay_grievances'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('owner_user_id', sa.String(), nullable=True))
            batch_op.create_index(batch_op.f(f'ix_{table}_owner_user_id'), ['owner_user_id'], unique=False)
            batch_op.create_foreign_key(f'fk_{table}_owner_user_id_kadi_users', 'kadi_users', ['owner_user_id'], ['id'])


def downgrade() -> None:
    for table in ('bimanyay_grievances', 'bimanyay_cases'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f'fk_{table}_owner_user_id_kadi_users', type_='foreignkey')
            batch_op.drop_index(batch_op.f(f'ix_{table}_owner_user_id'))
            batch_op.drop_column('owner_user_id')

    with op.batch_alter_table('kadi_cases', schema=None) as batch_op:
        batch_op.drop_constraint('fk_kadi_cases_owner_user_id_kadi_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_kadi_cases_owner_user_id'))
        batch_op.drop_column('owner_user_id')

    with op.batch_alter_table('kadi_account_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_kadi_account_tokens_user_id'))
    op.drop_table('kadi_account_tokens')

    with op.batch_alter_table('kadi_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_kadi_sessions_user_id'))
    op.drop_table('kadi_sessions')

    op.drop_table('kadi_users')
