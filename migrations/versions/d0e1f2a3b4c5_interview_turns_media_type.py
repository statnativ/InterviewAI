"""interview_turns: media_type (M4b: async video capture)

Adds `interview_turns.media_type` (`'audio'` | `'video'`, default `'audio'`)
recording whether the candidate's answer was captured as audio-only (Voice
mode) or video (new Video mode, sibling to Voice — no CHECK constraint
existed on interviews.mode, so the mode value itself needed no migration).

`candidate_audio_path`/`candidate_audio_format` are NOT renamed despite now
potentially holding a video file — an additive column here is cheaper than
touching every M4 call site for a cosmetic rename, consistent with this
project's additive-migration discipline (see e5f6a7b8c9d0, c3d4e5f6a7b8 for
the same add-nullable-with-default pattern, never a destructive rename).

Same String(20) + CHECK convention as score_method/judge_status/
ck_interview_turns_status before it.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-10 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interview_turns',
        sa.Column('media_type', sa.String(20), nullable=False, server_default='audio'),
    )
    op.create_check_constraint(
        'ck_interview_turns_media_type',
        'interview_turns',
        "media_type IN ('audio', 'video')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_interview_turns_media_type', 'interview_turns', type_='check')
    op.drop_column('interview_turns', 'media_type')
