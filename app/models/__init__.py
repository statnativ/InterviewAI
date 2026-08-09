"""Importing this package registers every table on Base.metadata.

Anything that touches the ORM — the app server, Alembic, scripts — needs all
models loaded up front, since cross-table foreign keys (e.g. jobs.posted_by ->
users.id) only resolve if every referenced table's model has been imported
somewhere first.
"""

from app.models.tenant import Tenant
from app.models.user import User
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.skill import Skill
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.job_skill import JobSkill
from app.models.application import Application
from app.models.interview import Interview
from app.models.ai_processing_log import AIProcessingLog
from app.models.session import Session
from app.models.practice_test import PracticeTest

__all__ = [
    "Tenant",
    "User",
    "Candidate",
    "Job",
    "Skill",
    "Resume",
    "ResumeSkill",
    "JobSkill",
    "Application",
    "Interview",
    "AIProcessingLog",
    "Session",
    "PracticeTest",
]
