"""interview_sessions + interview_turns (M4: wire the voice cascade into the app)

Two new tables persisting a candidate's Voice-mode interview attempt.
`interview_sessions.id` is the bearer credential for every turn request —
no candidate login/auth system exists anywhere in this codebase (see
ADR-008, which records that decision alongside the audio-storage one
below). `interview_turns` uses `UNIQUE(session_id, turn_index)` as the
idempotency key ADR-007's persist-before-calling pattern depends on: the
client resends the same turn_index on retry, and the row is found rather
than duplicated.

Interview audio (candidate and AI) is stored unencrypted on local disk,
same pattern as `app/storage/local.py`'s existing résumé uploads
(`candidate_audio_path`/`ai_audio_path` below are paths, not blobs). This
is a deliberate, risk-accepted extension of R-006 (PII/retention gap),
not a fix for it — ADR-007 flagged this as "not deferrable past M4's
build"; ADR-008 records the acceptance rather than solving encryption
inside this milestone.

Both tables follow `applications.judge_status`'s exact convention
(String(20) + CHECK ... IN (...), not a boolean) — same discipline as
`score_method`/`judge_status` from the same session.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-10 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interview_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_interview_sessions_tenant', 'interview_sessions', ['tenant_id'])
    op.create_index('idx_interview_sessions_interview', 'interview_sessions', ['interview_id'])
    op.create_check_constraint(
        'ck_interview_sessions_status',
        'interview_sessions',
        "status IN ('active', 'complete', 'abandoned')",
    )

    op.create_table(
        'interview_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('candidate_audio_path', sa.String(500), nullable=True),
        sa.Column('candidate_audio_format', sa.String(20), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('ai_text', sa.Text(), nullable=True),
        sa.Column('ai_audio_path', sa.String(500), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_interview_turns_session', 'interview_turns', ['session_id'])
    op.create_unique_constraint(
        'uq_interview_turns_session_turn', 'interview_turns', ['session_id', 'turn_index']
    )
    op.create_check_constraint(
        'ck_interview_turns_status',
        'interview_turns',
        "status IN ('pending', 'complete', 'failed')",
    )


def downgrade() -> None:
    op.drop_table('interview_turns')
    op.drop_table('interview_sessions')
