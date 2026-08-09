import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.candidate import CandidateView
from app.schemas.job import JobCreate, JobPatch, JobView
from app.services.screening import generate_rubric
from app.services.views import candidate_to_view, job_to_view

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _get_job_or_404(job_id: uuid.UUID, db: AsyncSession) -> Job:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[JobView])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    return [job_to_view(j) for j in result.scalars().all()]


@router.post("", response_model=JobView, status_code=201)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    rubric = generate_rubric(payload.description) if payload.description.strip() else []
    job = Job(
        title=payload.title,
        description=payload.description,
        department=payload.department,
        location=payload.location,
        employment_type=payload.type,
        status=payload.status,
        rubric=rubric,
        versions=[
            {
                "version": 1,
                "label": "Version 1",
                "status": "Approved",
                "by": "Recruiter",
                "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
            }
        ],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job_to_view(job)


@router.get("/{job_id}", response_model=JobView)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return job_to_view(await _get_job_or_404(job_id, db))


@router.patch("/{job_id}", response_model=JobView)
async def patch_job(job_id: uuid.UUID, payload: JobPatch, db: AsyncSession = Depends(get_db)):
    job = await _get_job_or_404(job_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "type" in data:
        job.employment_type = data.pop("type")
    for key, value in data.items():
        setattr(job, key, value)
    await db.commit()
    await db.refresh(job)
    return job_to_view(job)


@router.post("/{job_id}/regenerate-rubric", response_model=JobView)
async def regenerate_rubric(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await _get_job_or_404(job_id, db)
    rubric = generate_rubric(job.description)
    if not rubric:
        raise HTTPException(status_code=400, detail="Could not extract any skills from the job description.")
    job.rubric = rubric
    prev = job.versions[-1] if job.versions else {"version": 0}
    job.versions = [
        *(dict(v, status="Superseded") if v.get("status") == "Approved" else v for v in job.versions),
        {
            "version": int(prev.get("version", 0)) + 1,
            "label": f"Version {int(prev.get('version', 0)) + 1}",
            "status": "Approved",
            "by": "Recruiter",
            "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
        },
    ]
    # Re-screen every application for this job against the new rubric.
    await _rescreen_job(job.id, db)
    await db.commit()
    await db.refresh(job)
    return job_to_view(job)


@router.post("/{job_id}/save-version", response_model=JobView)
async def save_job_version(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await _get_job_or_404(job_id, db)
    prev = job.versions[-1] if job.versions else {"version": 0}
    version = int(prev.get("version", 0)) + 1
    job.versions = [
        *(dict(v, status="Superseded") if v.get("status") == "Approved" else v for v in job.versions),
        {
            "version": version,
            "label": f"Version {version}",
            "status": "Approved",
            "by": "Recruiter",
            "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
        },
    ]
    await db.commit()
    await db.refresh(job)
    return job_to_view(job)


@router.get("/{job_id}/candidates", response_model=list[CandidateView])
async def list_job_candidates(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_job_or_404(job_id, db)
    result = await db.execute(
        select(Application, Candidate)
        .join(Candidate, Application.candidate_id == Candidate.id)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.candidate))
        .order_by(Application.match_score.desc().nullslast())
    )
    return [candidate_to_view(app, cand) for app, cand in result.all()]


async def _rescreen_job(job_id: uuid.UUID, db: AsyncSession) -> None:
    """Re-run screening for every application of a job. Caller commits."""
    from app.services.screening import derive_score

    job = await db.get(Job, job_id)
    if not job:
        return
    result = await db.execute(select(Application).where(Application.job_id == job_id))
    apps = result.scalars().all()
    for app in apps:
        cand = await db.get(Candidate, app.candidate_id)
        if cand is None:
            continue
        screening = derive_score(job.rubric or [], cand.skills or [])
        app.match_score = screening["score"]
        app.scorecard = screening["scorecard"]
        app.ai_note = screening["ai_note"]
        app.compare_verdict = screening["compare_verdict"]
        app.shortlisted = screening["shortlisted"]
        app.strengths = [s["criterion"] for s in screening["scorecard"] if s["score"] >= 100]
        app.gaps = [s["criterion"] for s in screening["scorecard"] if s["score"] < 100]
