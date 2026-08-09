"""interview job/candidate links: M3 question generation

Adds `interviews.job_id` (nullable FK to jobs, backfilled by matching the
existing `job_title` string against `jobs.title` within the same tenant, only
where the match is unambiguous — one job with that title) and
`interviews.candidate_id` (nullable FK to candidates, no backfill — new
concept). Both support app/services/question_generator.py: job_id supplies
the JD text for generation/regeneration, candidate_id marks an interview as
personalized for one candidate rather than a shared template. `job_title`
column is untouched — it stays as the display fallback for interviews whose
job_id doesn't resolve.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('interviews', sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_interviews_job_id', 'interviews', 'jobs', ['job_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_interviews_candidate_id', 'interviews', 'candidates', ['candidate_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('idx_interviews_job', 'interviews', ['job_id'])
    op.create_index('idx_interviews_candidate', 'interviews', ['candidate_id'])

    # Backfill job_id only where (tenant_id, job_title) matches exactly one job's
    # (tenant_id, title) — leave it null everywhere else rather than guessing.
    op.execute(
        """
        UPDATE interviews AS iv
        SET job_id = j.id
        FROM jobs AS j
        WHERE j.tenant_id = iv.tenant_id
          AND j.title = iv.job_title
          AND (
              SELECT count(*) FROM jobs AS j2
              WHERE j2.tenant_id = iv.tenant_id AND j2.title = iv.job_title
          ) = 1
        """
    )


def downgrade() -> None:
    op.drop_index('idx_interviews_candidate', table_name='interviews')
    op.drop_index('idx_interviews_job', table_name='interviews')
    op.drop_constraint('fk_interviews_candidate_id', 'interviews', type_='foreignkey')
    op.drop_constraint('fk_interviews_job_id', 'interviews', type_='foreignkey')
    op.drop_column('interviews', 'candidate_id')
    op.drop_column('interviews', 'job_id')
