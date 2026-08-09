"""Mapping helpers from ORM rows -> the flat view shapes the frontend consumes."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.schemas.candidate import CandidateView
from app.schemas.interview import InterviewView
from app.schemas.job import JobView


def _iso(dt: datetime) -> datetime:
    # Pydantic serializes datetimes; keep the object and let the schema format it.
    return dt


def job_to_view(job: Job) -> JobView:
    return JobView(
        id=str(job.id),
        title=job.title,
        department=job.department,
        location=job.location,
        type=job.employment_type,
        status=job.status,
        description=job.description,
        rubric=job.rubric or [],
        versions=job.versions or [],
        createdAt=_iso(job.created_at),
    )


def candidate_to_view(app: Application, candidate: Candidate) -> CandidateView:
    score = app.match_score
    return CandidateView(
        id=str(app.id),
        jobId=str(app.job_id),
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        source=candidate.source or "Manual Entry",
        tags=candidate.tags or [],
        notes=candidate.notes or "",
        resumeFile=candidate.resume_file,
        yearsExp=candidate.years_exp,
        currentTitle=candidate.current_title,
        currentCompany=candidate.current_company,
        skills=candidate.skills or [],
        score=int(score) if score is not None else 0,
        shortlisted=app.shortlisted,
        decision=app.decision,
        pipelineStage=app.pipeline_stage,
        summary=candidate.summary or "",
        experience=candidate.experience or [],
        education=candidate.education or "—",
        certifications=candidate.certifications or "—",
        scorecard=app.scorecard or [],
        strengths=app.strengths or [],
        gaps=app.gaps or [],
        aiNote=app.ai_note or "",
        compareVerdict=app.compare_verdict or "Pass",
        appliedAt=_iso(app.applied_at),
    )


def interview_to_view(iv: Interview, candidate_name: str | None = None) -> InterviewView:
    return InterviewView(
        id=str(iv.id),
        title=iv.title,
        jobTitle=iv.job_title,
        jobId=str(iv.job_id) if iv.job_id else None,
        candidateId=str(iv.candidate_id) if iv.candidate_id else None,
        candidateName=candidate_name,
        mode=iv.mode,
        status=iv.status,
        questions=iv.questions or [],
        duration=iv.duration,
        createdAt=_iso(iv.created_at),
        shared=iv.shared,
    )
