"""applications: judge_status + judge_error (IA-003, LLM-as-judge off the request path)

Adds `applications.judge_status` (`'idle'` | `'pending'` | `'failed'`) and
`applications.judge_error` (nullable text). POST /candidates/{id}/judge now
returns 202 and runs judge_candidate() via FastAPI BackgroundTasks — the
first use of BackgroundTasks anywhere in this codebase. Failure can no
longer surface as a synchronous 502 (the client isn't waiting on the
request), so it has to live somewhere pollable instead: judge_error.

Same discipline as score_method (migration a7b8c9d0e1f2) and
ck_interviews_no_shared_personalized before it — a real, inspectable
column + CHECK constraint from day one, not inferred state.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'applications',
        sa.Column('judge_status', sa.String(20), nullable=False, server_default='idle'),
    )
    op.add_column('applications', sa.Column('judge_error', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_applications_judge_status',
        'applications',
        "judge_status IN ('idle', 'pending', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_applications_judge_status', 'applications', type_='check')
    op.drop_column('applications', 'judge_error')
    op.drop_column('applications', 'judge_status')
