import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.interview import Interview
from app.schemas.interview import InterviewCreate, InterviewPatch, InterviewView
from app.services.views import interview_to_view

router = APIRouter(prefix="/interviews", tags=["interviews"])


async def _get_or_404(iv_id: uuid.UUID, db: AsyncSession) -> Interview:
    iv = await db.get(Interview, iv_id)
    if iv is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return iv


@router.get("", response_model=list[InterviewView])
async def list_interviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Interview).order_by(Interview.created_at.desc()))
    return [interview_to_view(iv) for iv in result.scalars().all()]


@router.post("", response_model=InterviewView, status_code=201)
async def create_interview(payload: InterviewCreate, db: AsyncSession = Depends(get_db)):
    iv = Interview(
        title=payload.title,
        job_title=payload.jobTitle,
        mode=payload.mode,
        duration=payload.duration,
        questions=payload.questions,
    )
    db.add(iv)
    await db.commit()
    await db.refresh(iv)
    return interview_to_view(iv)


@router.get("/{iv_id}", response_model=InterviewView)
async def get_interview(iv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return interview_to_view(await _get_or_404(iv_id, db))


@router.patch("/{iv_id}", response_model=InterviewView)
async def patch_interview(iv_id: uuid.UUID, payload: InterviewPatch, db: AsyncSession = Depends(get_db)):
    iv = await _get_or_404(iv_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "jobTitle" in data:
        iv.job_title = data.pop("jobTitle")
    for key, value in data.items():
        setattr(iv, key, value)
    await db.commit()
    await db.refresh(iv)
    return interview_to_view(iv)
