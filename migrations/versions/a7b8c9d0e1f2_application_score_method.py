"""applications: score_method column (LLM-as-judge, M2)

Adds `applications.score_method` — `'deterministic'` (the existing keyword-
match scorer, `app/services/screening.py::derive_score`) or `'llm_judge'`
(the new `app/services/candidate_judge.py::judge_candidate`, an explicit,
recruiter-triggered action, not run automatically on candidate creation).

Built as a real, non-nullable column with a DB `CHECK` constraint from the
start — R-011 (`docs/risk-register.md`) already showed what happens when two
modes of the same entity share state with no discriminator (`Interview`'s
shared/personalized ambiguity, retrofitted after the fact). Every write path
(`_apply_screening`, the new `/judge` endpoint) stamps this explicitly;
nothing is ever left as a stale value from a prior run of the other method.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'applications',
        sa.Column('score_method', sa.String(20), nullable=False, server_default='deterministic'),
    )
    op.create_check_constraint(
        'ck_applications_score_method',
        'applications',
        "score_method IN ('deterministic', 'llm_judge')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_applications_score_method', 'applications', type_='check')
    op.drop_column('applications', 'score_method')
