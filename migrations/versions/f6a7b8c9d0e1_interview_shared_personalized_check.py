"""interviews: forbid shared + personalized simultaneously (R-011)

Adds a CHECK constraint preventing an `Interview` row from having both
`shared = true` and `candidate_id IS NOT NULL` — M3's per-candidate
personalization shipped without a guard against sharing a personalized
interview with every other applicant, surfacing one candidate's
résumé-derived questions to everyone else. See docs/risk-register.md R-011
and docs/implementation-actions.md IA-012.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        'ck_interviews_no_shared_personalized',
        'interviews',
        'NOT (shared AND candidate_id IS NOT NULL)',
    )


def downgrade() -> None:
    op.drop_constraint('ck_interviews_no_shared_personalized', 'interviews', type_='check')
