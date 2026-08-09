"""admin auth module: platform admins, sessions, practice tests

Adds the master-admin login surface: `users.tenant_id` becomes nullable (a
platform admin belongs to no tenant), with a CHECK constraint enforcing the
invariant at the DB layer (tenant_id IS NULL iff is_platform_admin). New
`username`/`password_hash`/`status` columns support real login for the first
time (previously every route trusted client-supplied headers — see migration
c3d4e5f6a7b8 / M6 Phase 1-2). New `sessions` table (server-side, revocable —
the row's own id is the cookie token) and `practice_tests` table
(tenant-specific practice content authored by the platform admin).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-09 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: real-auth columns + nullable tenant_id for platform admins ---
    op.alter_column('users', 'tenant_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column('users', sa.Column('username', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default='false'))

    op.create_index(
        'uq_users_username', 'users', ['username'], unique=True,
        postgresql_where=sa.text('username IS NOT NULL'),
    )
    op.create_check_constraint(
        'ck_users_platform_admin_no_tenant',
        'users',
        '(tenant_id IS NULL AND is_platform_admin) OR (tenant_id IS NOT NULL AND NOT is_platform_admin)',
    )

    # --- sessions ---
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- practice_tests ---
    op.create_table(
        'practice_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('mode', sa.String(length=50), nullable=False, server_default='Chat'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
        sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('duration', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_practice_tests_tenant', 'practice_tests', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('practice_tests')
    op.drop_table('sessions')
    op.drop_constraint('ck_users_platform_admin_no_tenant', 'users', type_='check')
    op.drop_index('uq_users_username', table_name='users')
    op.drop_column('users', 'is_platform_admin')
    op.drop_column('users', 'status')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'username')
    op.alter_column('users', 'tenant_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
