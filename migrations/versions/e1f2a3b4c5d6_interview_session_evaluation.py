"""interview_sessions: evaluation + human-override columns (M5)

Adds the AI-evaluation and recruiter-override fields to `interview_sessions`,
purely additive — no existing column touched. Mirrors `applications`' own
screening-output shape (`score`/`scorecard`/`strengths`/`gaps`, `decision`)
so a recruiter reviewing an interview sees the same conventions as reviewing
a résumé screen.

`evaluation_status` is a deliberate 4-state design (`idle`/`pending`/
`complete`/`failed`) — richer than `applications.judge_status`'s 3-state
convention (`idle`/`pending`/`failed`), because `Application` has a second
field (`score_method`) a caller can check to infer "done" from `judge_status`
being back at `idle`; `InterviewSession` has no such field, so `evaluation_status`
needs its own explicit terminal "complete" value instead of inferring it from
absence. See ADR-009.

`ai_verdict` and `decision` deliberately get NO CHECK constraint, matching
`applications.compare_verdict`/`applications.decision`'s own precedent
(enum-like values documented by comment only, not enforced at the DB layer) —
`evaluation_status` is the one enum-like field here that *does* get a CHECK,
matching `applications.judge_status`'s precedent instead, because it's a real
state machine with an explicit lifecycle, not free-text-ish output.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interview_sessions',
        sa.Column('evaluation_status', sa.String(20), nullable=False, server_default='idle'),
    )
    op.create_check_constraint(
        'ck_interview_sessions_evaluation_status',
        'interview_sessions',
        "evaluation_status IN ('idle', 'pending', 'complete', 'failed')",
    )
    op.add_column('interview_sessions', sa.Column('score', sa.Integer(), nullable=True))
    op.add_column(
        'interview_sessions',
        sa.Column('scorecard', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
    )
    op.add_column(
        'interview_sessions',
        sa.Column('strengths', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
    )
    op.add_column(
        'interview_sessions',
        sa.Column('gaps', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
    )
    op.add_column('interview_sessions', sa.Column('ai_verdict', sa.String(20), nullable=True))
    op.add_column('interview_sessions', sa.Column('ai_note', sa.Text(), nullable=True))
    op.add_column('interview_sessions', sa.Column('evaluation_error', sa.Text(), nullable=True))
    op.add_column(
        'interview_sessions', sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'interview_sessions',
        sa.Column('decision', sa.String(50), nullable=False, server_default='None'),
    )


def downgrade() -> None:
    op.drop_column('interview_sessions', 'decision')
    op.drop_column('interview_sessions', 'evaluated_at')
    op.drop_column('interview_sessions', 'evaluation_error')
    op.drop_column('interview_sessions', 'ai_note')
    op.drop_column('interview_sessions', 'ai_verdict')
    op.drop_column('interview_sessions', 'gaps')
    op.drop_column('interview_sessions', 'strengths')
    op.drop_column('interview_sessions', 'scorecard')
    op.drop_column('interview_sessions', 'score')
    op.drop_constraint('ck_interview_sessions_evaluation_status', 'interview_sessions', type_='check')
    op.drop_column('interview_sessions', 'evaluation_status')
