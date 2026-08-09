"""align schema for the ATS frontend contract

Adds the fields the frontend needs but the M1 schema lacked:
  * jobs:    rubric + versions (JSONB)
  * candidates:  source, tags, notes, resume_file, current_role, skills,
                 summary, experience, education, certifications
  * applications: screening output (shortlisted, decision, pipeline_stage,
                  scorecard, strengths, gaps, compare_verdict, ai_note)
  * new interviews table (config-only; chat transcripts stay in the session)

Revision ID: a1b2c3d4e5f6
Revises: 68b7d2e3a988
Create Date: 2026-08-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '68b7d2e3a988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # jobs — rubric + version history are document-shaped; keep them JSONB.
    op.add_column('jobs', sa.Column('rubric', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('jobs', sa.Column('versions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))

    # candidates — flat profile fields that the frontend Candidate type exposes.
    op.add_column('candidates', sa.Column('source', sa.String(length=100), nullable=False, server_default='Manual Entry'))
    op.add_column('candidates', sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('candidates', sa.Column('notes', sa.Text(), nullable=False, server_default=''))
    op.add_column('candidates', sa.Column('resume_file', sa.String(length=255), nullable=True))
    op.add_column('candidates', sa.Column('years_exp', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('candidates', sa.Column('current_title', sa.String(length=255), nullable=False, server_default='—'))
    op.add_column('candidates', sa.Column('current_company', sa.String(length=255), nullable=False, server_default='—'))
    op.add_column('candidates', sa.Column('skills', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('candidates', sa.Column('summary', sa.Text(), nullable=False, server_default=''))
    op.add_column('candidates', sa.Column('experience', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('candidates', sa.Column('education', sa.Text(), nullable=False, server_default='—'))
    op.add_column('candidates', sa.Column('certifications', sa.Text(), nullable=False, server_default='—'))

    # applications — screening outputs that currently only exist client-side.
    op.add_column('applications', sa.Column('shortlisted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('applications', sa.Column('decision', sa.String(length=50), nullable=False, server_default='None'))
    op.add_column('applications', sa.Column('pipeline_stage', sa.String(length=50), nullable=False, server_default='Applied'))
    op.add_column('applications', sa.Column('scorecard', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('applications', sa.Column('strengths', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('applications', sa.Column('gaps', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('applications', sa.Column('compare_verdict', sa.String(length=20), nullable=False, server_default='Pass'))
    op.add_column('applications', sa.Column('ai_note', sa.Text(), nullable=False, server_default=''))

    # interviews — the config records the org creates and shares.
    op.create_table('interviews',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=False),
    sa.Column('mode', sa.String(length=50), nullable=False, server_default='Chat'),
    sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
    sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
    sa.Column('duration', sa.Integer(), nullable=False, server_default='30'),
    sa.Column('shared', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('interviews')
    op.drop_column('applications', 'ai_note')
    op.drop_column('applications', 'compare_verdict')
    op.drop_column('applications', 'gaps')
    op.drop_column('applications', 'strengths')
    op.drop_column('applications', 'scorecard')
    op.drop_column('applications', 'pipeline_stage')
    op.drop_column('applications', 'decision')
    op.drop_column('applications', 'shortlisted')
    op.drop_column('candidates', 'certifications')
    op.drop_column('candidates', 'education')
    op.drop_column('candidates', 'experience')
    op.drop_column('candidates', 'summary')
    op.drop_column('candidates', 'skills')
    op.drop_column('candidates', 'current_company')
    op.drop_column('candidates', 'current_title')
    op.drop_column('candidates', 'years_exp')
    op.drop_column('candidates', 'resume_file')
    op.drop_column('candidates', 'notes')
    op.drop_column('candidates', 'tags')
    op.drop_column('candidates', 'source')
    op.drop_column('jobs', 'versions')
    op.drop_column('jobs', 'rubric')
