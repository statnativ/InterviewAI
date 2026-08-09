import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_tenant, require_roles
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.candidate import (
    AddCandidateResult,
    BulkPatch,
    CandidateCreate,
    CandidatePatch,
    CandidateView,
)
from app.schemas.candidate import ResumeOut
from app.services.authz import ALL_ROLES, WRITE_ROLES
from app.services.screening import (
    build_gaps,
    build_strengths,
    derive_score,
    extract_skills,
)
from app.services.views import candidate_to_view
from app.storage.local import save_upload

router = APIRouter(prefix="/candidates", tags=["candidates"])


async def _get_app_or_404(
    app_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> tuple[Application, Candidate]:
    result = await db.execute(
        select(Application, Candidate)
        .join(Candidate, Application.candidate_id == Candidate.id)
        .where(Application.id == app_id, Application.tenant_id == tenant_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return row[0], row[1]


@router.get("", response_model=list[CandidateView])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    result = await db.execute(
        select(Application, Candidate)
        .join(Candidate, Application.candidate_id == Candidate.id)
        .where(Application.tenant_id == tenant.id)
        .order_by(Application.match_score.desc().nullslast())
    )
    return [candidate_to_view(app, cand) for app, cand in result.all()]


@router.post("", response_model=AddCandidateResult, status_code=201)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    result = await db.execute(
        select(Job).where(Job.id == uuid.UUID(payload.jobId), Job.tenant_id == tenant.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    email_key = payload.email.strip().lower()
    existing = (
        await db.execute(
            select(Candidate).where(Candidate.email == email_key, Candidate.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        # Duplicate person — do not create a new record. Surface the existing
        # application (or the person's first) so the UI can warn.
        existing_app = (
            await db.execute(
                select(Application)
                .where(Application.candidate_id == existing.id, Application.job_id == job.id)
            )
        ).scalar_one_or_none()
        if existing_app is None:
            existing_app = (
                await db.execute(
                    select(Application).where(Application.candidate_id == existing.id)
                )
            ).scalars().first()
        return AddCandidateResult(
            candidate=candidate_to_view(existing_app, existing), duplicate=True
        )

    skills = extract_skills(payload.resumeText)
    candidate = Candidate(
        tenant_id=tenant.id,
        name=payload.name,
        email=email_key,
        phone=payload.phone,
        source=payload.source or "Manual Entry",
        skills=skills,
        summary=payload.resumeText[:220] or "Resume pasted — awaiting full parse.",
        current_title="—",
        current_company="—",
    )
    db.add(candidate)
    await db.flush()

    app = Application(tenant_id=tenant.id, candidate_id=candidate.id, job_id=job.id, status="screening")
    db.add(app)
    await db.flush()

    _apply_screening(app, job, candidate)

    await db.commit()
    return AddCandidateResult(candidate=candidate_to_view(app, candidate), duplicate=False)


@router.get("/{app_id}", response_model=CandidateView)
async def get_candidate(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    app, cand = await _get_app_or_404(app_id, tenant.id, db)
    return candidate_to_view(app, cand)


@router.patch("/{app_id}", response_model=CandidateView)
async def patch_candidate(
    app_id: uuid.UUID,
    payload: CandidatePatch,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    app, cand = await _get_app_or_404(app_id, tenant.id, db)
    data = payload.model_dump(exclude_unset=True)
    app_fields = {"shortlisted", "decision", "pipelineStage"}
    for key, value in data.items():
        if key in app_fields:
            setattr(app, {"pipelineStage": "pipeline_stage"}.get(key, key), value)
        else:
            setattr(cand, key, value)
    await db.commit()
    await db.refresh(app)
    await db.refresh(cand)
    return candidate_to_view(app, cand)


@router.post("/{app_id}/screen", response_model=CandidateView)
async def screen_candidate(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    app, cand = await _get_app_or_404(app_id, tenant.id, db)
    job = await db.get(Job, app.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    _apply_screening(app, job, cand)
    await db.commit()
    await db.refresh(app)
    return candidate_to_view(app, cand)


@router.post("/bulk", response_model=list[CandidateView])
async def bulk_patch(
    payload: BulkPatch,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    ids = [uuid.UUID(cid) for cid in payload.candidateIds]
    result = await db.execute(
        select(Application, Candidate)
        .join(Candidate, Application.candidate_id == Candidate.id)
        .where(Application.id.in_(ids), Application.tenant_id == tenant.id)
    )
    rows = result.all()
    for app, _ in rows:
        if payload.action == "shortlist":
            app.shortlisted = True
        elif payload.action == "unshortlist":
            app.shortlisted = False
        elif payload.action == "decision":
            app.decision = str(payload.value)
        elif payload.action == "stage":
            app.pipeline_stage = str(payload.value)
    await db.commit()
    return [candidate_to_view(app, cand) for app, cand in rows]


@router.post("/{app_id}/resume", response_model=ResumeOut, status_code=201)
async def upload_resume(
    app_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """Attach a resume file to an application, extract text, and re-screen."""
    from app.services.resume_parser import extract_text

    app, cand = await _get_app_or_404(app_id, tenant.id, db)
    file_bytes = await file.read()
    try:
        text = extract_text(file_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    file_path = save_upload(file_bytes, file.filename, cand.id)
    resume = Resume(
        tenant_id=tenant.id,
        candidate_id=cand.id,
        file_name=file.filename,
        file_path=str(file_path),
        file_type=Path(file.filename).suffix.lstrip(".").lower() or None,
        file_size=len(file_bytes),
        raw_text=text,
        parsed_data={"skills": extract_skills(text)},
    )
    db.add(resume)
    cand.skills = extract_skills(text)
    job = await db.get(Job, app.job_id)
    if job is not None:
        _apply_screening(app, job, cand)
    await db.commit()
    await db.refresh(resume)
    return resume


def _apply_screening(app: Application, job: Job, cand: Candidate) -> None:
    if not (job.rubric or []):
        return
    result = derive_score(job.rubric, cand.skills or [])
    app.match_score = result["score"]
    app.scorecard = result["scorecard"]
    app.ai_note = result["ai_note"]
    app.compare_verdict = result["compare_verdict"]
    app.shortlisted = result["shortlisted"]
    app.strengths = build_strengths(result["scorecard"])
    app.gaps = build_gaps(result["scorecard"])
    app.status = "screening"
