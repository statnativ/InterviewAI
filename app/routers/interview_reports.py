"""M5: recruiter-facing review of a completed interview session — score, scorecard,
transcript, playback, and the human-override decision. A deliberately separate router from
app/routers/interview_sessions.py, whose file-level docstring is explicit about being the
candidate-facing, no-tenant/role-auth surface (ADR-008); mixing a get_current_tenant-gated
route into that file would contradict its own documented contract. Every route here uses the
same tenant/role auth every other recruiter-facing router does.

`GET .../turns/{turn_index}/media` is the first file-serving endpoint in this app — M4/M4b's
"no file-serving precedent, base64-inline is fine" reasoning was scoped to the candidate's own
live session, not a recruiter reviewing playback afterward.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import evaluate_interview_task
from app.db import get_db
from app.deps import get_current_tenant, require_roles
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.interview_report import DecisionPatch, InterviewReportView, InterviewSessionSummaryView
from app.services.authz import ALL_ROLES, WRITE_ROLES
from app.services.views import interview_session_to_report_view, interview_session_to_summary_view

router = APIRouter(tags=["interview-reports"])


async def _get_session_or_404(session_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> InterviewSession:
    # Direct tenant_id filtering — InterviewSession already carries it (set transitively from
    # Interview.tenant_id at session-creation time), so no join through Interview is needed for
    # the ownership check itself, same as Application.tenant_id elsewhere in this codebase.
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id, InterviewSession.tenant_id == tenant_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


async def _candidate_name(candidate_id: uuid.UUID | None, db: AsyncSession) -> str | None:
    if candidate_id is None:
        return None
    candidate = await db.get(Candidate, candidate_id)
    return candidate.name if candidate else None


@router.get("/interviews/{interview_id}/sessions", response_model=list[InterviewSessionSummaryView])
async def list_interview_sessions(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    interview = await db.get(Interview, interview_id)
    if interview is None or interview.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Interview not found")

    sessions = (
        await db.execute(
            select(InterviewSession)
            .where(InterviewSession.interview_id == interview_id, InterviewSession.tenant_id == tenant.id)
            .order_by(InterviewSession.created_at.desc())
        )
    ).scalars().all()

    return [
        interview_session_to_summary_view(s, await _candidate_name(s.candidate_id, db)) for s in sessions
    ]


@router.get("/interview-sessions/{session_id}/report", response_model=InterviewReportView)
async def get_interview_report(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    session = await _get_session_or_404(session_id, tenant.id, db)
    turns = (
        await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session_id).order_by(InterviewTurn.turn_index)
        )
    ).scalars().all()
    candidate_name = await _candidate_name(session.candidate_id, db)
    return interview_session_to_report_view(session, list(turns), candidate_name)


@router.patch("/interview-sessions/{session_id}", response_model=InterviewReportView)
async def patch_interview_session_decision(
    session_id: uuid.UUID,
    payload: DecisionPatch,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """The human-override endpoint (M5). Only ever touches `decision` — never the AI-owned
    evaluation fields above it, same separation Application.decision already keeps from its
    own scorecard. No gate on evaluationStatus: a recruiter can set a decision any time,
    matching Application.decision's existing precedent."""
    session = await _get_session_or_404(session_id, tenant.id, db)
    session.decision = payload.decision
    await db.commit()
    await db.refresh(session)

    turns = (
        await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session_id).order_by(InterviewTurn.turn_index)
        )
    ).scalars().all()
    candidate_name = await _candidate_name(session.candidate_id, db)
    return interview_session_to_report_view(session, list(turns), candidate_name)


@router.post("/interview-sessions/{session_id}/evaluate", response_model=InterviewReportView, status_code=202)
async def retry_interview_evaluation(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """Manual retry/re-trigger — a backstop for a failed or stuck evaluation, mirroring
    candidate_judge.py's explicit-trigger precedent. The 3 automatic sites in
    interview_sessions.py cover normal completion; this exists for the case where enqueueing
    failed outright or a recruiter wants to re-run it."""
    session = await _get_session_or_404(session_id, tenant.id, db)
    if session.status != "complete":
        raise HTTPException(status_code=400, detail="This interview session isn't complete yet.")
    if session.evaluation_status == "pending":
        raise HTTPException(status_code=409, detail="An evaluation is already in progress.")

    session.evaluation_status = "pending"
    session.evaluation_error = None
    await db.commit()

    try:
        evaluate_interview_task.delay(str(session.id))
    except Exception as e:
        session.evaluation_status = "failed"
        session.evaluation_error = f"Could not enqueue evaluation: {e}"
        await db.commit()

    await db.refresh(session)
    turns = (
        await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session_id).order_by(InterviewTurn.turn_index)
        )
    ).scalars().all()
    candidate_name = await _candidate_name(session.candidate_id, db)
    return interview_session_to_report_view(session, list(turns), candidate_name)


@router.get("/interview-sessions/{session_id}/turns/{turn_index}/media")
async def get_turn_media(
    session_id: uuid.UUID,
    turn_index: int,
    speaker: str = Query(..., pattern="^(candidate|ai)$"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(require_roles(*ALL_ROLES)),
):
    await _get_session_or_404(session_id, tenant.id, db)
    turn = (
        await db.execute(
            select(InterviewTurn).where(
                InterviewTurn.session_id == session_id, InterviewTurn.turn_index == turn_index
            )
        )
    ).scalar_one_or_none()
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")

    if speaker == "ai":
        path_str = turn.ai_audio_path
        media_type = "audio/mpeg"  # always TTS mp3 regardless of media_type — M4b convention
    else:
        path_str = turn.candidate_audio_path
        kind = "video" if turn.media_type == "video" else "audio"
        media_type = f"{kind}/{turn.candidate_audio_format or 'webm'}"

    if not path_str:
        raise HTTPException(status_code=404, detail="No media recorded for this turn/speaker.")
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file not found on disk.")

    return FileResponse(path, media_type=media_type)
