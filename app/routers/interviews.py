import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_tenant, require_roles
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.interview import InterviewCreate, InterviewPatch, InterviewView
from app.services.authz import ALL_ROLES
from app.services.llm_client import LLMError
from app.services.question_generator import build_candidate_profile, generate_questions, regenerate_question
from app.services.views import interview_to_view

router = APIRouter(prefix="/interviews", tags=["interviews"])


async def _get_or_404(iv_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> Interview:
    result = await db.execute(
        select(Interview).where(Interview.id == iv_id, Interview.tenant_id == tenant_id)
    )
    iv = result.scalar_one_or_none()
    if iv is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return iv


async def _get_job(job_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> Job:
    job = await db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _resolve_candidate(candidate_ref_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> Candidate:
    """The frontend's "candidate id" for a job's applicant list is actually an
    Application id (CandidateView.id == Application.id — see
    services/views.py::candidate_to_view). Resolve that down to the real
    Candidate (the person, not the job application) that personalization
    should be built from."""
    application = await db.get(Application, candidate_ref_id)
    if application is None or application.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = await db.get(Candidate, application.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


async def _get_candidate(candidate_id: uuid.UUID | None, db: AsyncSession) -> Candidate | None:
    """candidate_id here is already a resolved Candidate.id (stored on the
    Interview row at creation time), not the frontend's application-id form —
    used wherever an interview is read back, not just at creation."""
    if candidate_id is None:
        return None
    return await db.get(Candidate, candidate_id)


@router.get("", response_model=list[InterviewView])
async def list_interviews(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    result = await db.execute(
        select(Interview, Candidate.name)
        .outerjoin(Candidate, Interview.candidate_id == Candidate.id)
        .where(Interview.tenant_id == tenant.id)
        .order_by(Interview.created_at.desc())
    )
    return [interview_to_view(iv, candidate_name) for iv, candidate_name in result.all()]


@router.post("", response_model=InterviewView, status_code=201)
async def create_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    job_id = uuid.UUID(payload.jobId) if payload.jobId else None
    candidate_ref_id = uuid.UUID(payload.candidateId) if payload.candidateId else None
    questions = payload.questions

    job = None
    candidate = None
    if job_id is not None:
        job = await _get_job(job_id, tenant.id, db)
        candidate_profile = None
        if candidate_ref_id is not None:
            candidate = await _resolve_candidate(candidate_ref_id, tenant.id, db)
            candidate_profile = build_candidate_profile(candidate)
        if not questions:
            try:
                questions = await generate_questions(job.title, job.description, candidate_profile)
            except LLMError as e:
                raise HTTPException(status_code=502, detail=f"Question generation failed — try again. ({e})")

    iv = Interview(
        tenant_id=tenant.id,
        title=payload.title,
        job_title=job.title if job else payload.jobTitle,
        job_id=job_id,
        candidate_id=candidate.id if candidate else None,
        mode=payload.mode,
        duration=payload.duration,
        questions=questions,
    )
    db.add(iv)
    await db.commit()
    await db.refresh(iv)
    return interview_to_view(iv, candidate.name if candidate else None)


@router.get("/{iv_id}", response_model=InterviewView)
async def get_interview(
    iv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    iv = await _get_or_404(iv_id, tenant.id, db)
    candidate = await _get_candidate(iv.candidate_id, db)
    return interview_to_view(iv, candidate.name if candidate else None)


@router.patch("/{iv_id}", response_model=InterviewView)
async def patch_interview(
    iv_id: uuid.UUID,
    payload: InterviewPatch,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    iv = await _get_or_404(iv_id, tenant.id, db)
    data = payload.model_dump(exclude_unset=True)
    if "jobTitle" in data:
        iv.job_title = data.pop("jobTitle")
    for key, value in data.items():
        setattr(iv, key, value)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "ck_interviews_no_shared_personalized" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail="Can't share an interview that's personalized for one candidate.",
            )
        raise
    await db.refresh(iv)
    candidate = await _get_candidate(iv.candidate_id, db)
    return interview_to_view(iv, candidate.name if candidate else None)


@router.post("/{iv_id}/regenerate", response_model=InterviewView)
async def regenerate_interview_questions(
    iv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    iv = await _get_or_404(iv_id, tenant.id, db)
    if iv.job_id is None:
        raise HTTPException(status_code=400, detail="This interview has no linked job to regenerate questions from.")
    job = await _get_job(iv.job_id, tenant.id, db)
    candidate = await _get_candidate(iv.candidate_id, db)
    candidate_profile = build_candidate_profile(candidate) if candidate else None
    try:
        iv.questions = await generate_questions(job.title, job.description, candidate_profile)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Question generation failed — try again. ({e})")
    await db.commit()
    await db.refresh(iv)
    return interview_to_view(iv, candidate.name if candidate else None)


@router.post("/{iv_id}/questions/{q_id}/regenerate", response_model=InterviewView)
async def regenerate_single_question(
    iv_id: uuid.UUID,
    q_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    iv = await _get_or_404(iv_id, tenant.id, db)
    if iv.job_id is None:
        raise HTTPException(status_code=400, detail="This interview has no linked job to regenerate questions from.")
    existing = next((q for q in iv.questions if q["id"] == q_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Question not found")
    others = [q for q in iv.questions if q["id"] != q_id]

    job = await _get_job(iv.job_id, tenant.id, db)
    candidate = await _get_candidate(iv.candidate_id, db)
    candidate_profile = build_candidate_profile(candidate) if candidate else None
    try:
        new_question = await regenerate_question(job.title, job.description, candidate_profile, existing, others)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Question generation failed — try again. ({e})")

    iv.questions = [new_question if q["id"] == q_id else q for q in iv.questions]
    await db.commit()
    await db.refresh(iv)
    return interview_to_view(iv, candidate.name if candidate else None)
