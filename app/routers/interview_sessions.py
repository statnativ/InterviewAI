"""M4/M4b: candidate-facing endpoints for taking a Voice- or Video-mode interview.

Deliberately NOT scoped like every other router in this codebase — no
`get_current_tenant`/`require_roles` here. There is no candidate identity
anywhere in this app; `interview_sessions.id` itself is the bearer
credential (see `get_current_interview_session` in app/deps.py and
ADR-008). Session creation is keyed on the interview's own id, which is
already an unguessable UUID and already the frontend's URL param.

M4b (video capture) touches only the mode gate and `InterviewTurn.media_type`
below — `interview_pipeline.py`'s cascade itself needed zero changes, the
concrete proof of PD-001's "swap the capture type, not the architecture"
claim. The interviewer's own response is always synthesized audio (TTS)
regardless of `media_type`; only the candidate's uploaded answer differs.
"""
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import async_session, get_db
from app.deps import get_current_interview_session
from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.job import Job
from app.schemas.interview_session import InterviewSessionView, TurnResultView, TurnSummaryView
from app.services.interview_pipeline import build_system_prompt, bound_history, run_turn, start_interview
from app.services.llm_client import LLMError
from app.storage.local import save_interview_audio

router = APIRouter(tags=["interview-sessions"])


def _turn_summaries(turns: list[InterviewTurn]) -> list[TurnSummaryView]:
    return [
        TurnSummaryView(
            turnIndex=t.turn_index, status=t.status, transcript=t.transcript, aiText=t.ai_text,
            mediaType=t.media_type,
        )
        for t in turns
    ]


def _cached_turn_result(session: InterviewSession, turn: InterviewTurn) -> TurnResultView:
    """A retry landing on an already-`complete` turn returns the same result instead of
    re-running the cascade — avoids double-billing the LLM/TTS calls and two "different"
    answers to what's supposed to be the same turn."""
    audio_bytes = Path(turn.ai_audio_path).read_bytes() if turn.ai_audio_path else b""
    return TurnResultView(
        sessionId=str(session.id),
        turnIndex=turn.turn_index,
        transcript=turn.transcript,
        aiText=turn.ai_text or "",
        aiAudio=base64.b64encode(audio_bytes).decode(),
        aiAudioFormat="mp3",
        status=session.status,
    )


def _reconstruct_history(interview: Interview, job: Job | None, prior_turns: list[InterviewTurn]) -> list[dict]:
    """Rebuilds the chat-message list run_turn expects from persisted turns — the system
    message itself is never stored on a row, only transcript/ai_text are, so it's rebuilt
    identically to how session creation first built it (same inputs -> same template)."""
    questions = [q["prompt"] for q in (interview.questions or [])]
    job_title = job.title if job else interview.job_title
    jd_text = job.description if job else ""
    history = [{"role": "system", "content": build_system_prompt(job_title, jd_text, questions)}]
    for turn in prior_turns:  # already ordered by turn_index, status == "complete" only
        if turn.turn_index == 0:
            history.append({"role": "assistant", "content": turn.ai_text})
        else:
            history.append({"role": "user", "content": turn.transcript})
            history.append({"role": "assistant", "content": turn.ai_text})
    return history


@router.post("/interviews/{interview_id}/sessions", response_model=TurnResultView, status_code=201)
async def create_interview_session(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    interview = await db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.mode not in ("Voice", "Video"):
        raise HTTPException(status_code=400, detail="This interview isn't a Voice or Video-mode interview.")
    media_type = "video" if interview.mode == "Video" else "audio"
    questions = [q["prompt"] for q in (interview.questions or [])]
    if not questions:
        raise HTTPException(status_code=400, detail="This interview has no questions to ask yet.")

    job = await db.get(Job, interview.job_id) if interview.job_id else None
    job_title = job.title if job else interview.job_title
    jd_text = job.description if job else ""

    try:
        result = await start_interview(job_title, jd_text, questions)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Couldn't start the interview — please retry. ({e})")

    now = datetime.now(timezone.utc)
    session = InterviewSession(
        tenant_id=interview.tenant_id,
        interview_id=interview.id,
        candidate_id=interview.candidate_id,
        status="complete" if result.is_complete else "active",
        completed_at=now if result.is_complete else None,
    )
    db.add(session)
    await db.flush()

    ai_audio_path = save_interview_audio(result.ai_audio, "turn_0_ai.mp3", session.id)
    db.add(
        InterviewTurn(
            session_id=session.id,
            turn_index=0,
            status="complete",
            media_type=media_type,  # turn 0 has no candidate media either way — recorded for consistency
            ai_text=result.ai_text,
            ai_audio_path=str(ai_audio_path),
            completed_at=now,
        )
    )
    await db.commit()

    return TurnResultView(
        sessionId=str(session.id),
        turnIndex=0,
        transcript=None,
        aiText=result.ai_text,
        aiAudio=base64.b64encode(result.ai_audio).decode(),
        aiAudioFormat="mp3",
        status=session.status,
    )


@router.post("/interview-sessions/{session_id}/turns", response_model=TurnResultView)
async def submit_turn(
    turn_index: int = Form(...),
    audio: UploadFile = File(...),
    audio_format: str = Form(...),
    session: InterviewSession = Depends(get_current_interview_session),
):
    if session.status != "active":
        raise HTTPException(status_code=409, detail="This interview session is no longer active.")

    # Phase 1 — short session: idempotency check + write/reset the pending row, then close
    # before the slow cascade call (ADR-007's connection-pool-exhaustion concern).
    async with async_session() as db:
        existing = (
            await db.execute(
                select(InterviewTurn).where(
                    InterviewTurn.session_id == session.id, InterviewTurn.turn_index == turn_index
                )
            )
        ).scalar_one_or_none()

        if existing is not None and existing.status == "complete":
            return _cached_turn_result(session, existing)
        if existing is not None and existing.status == "pending":
            raise HTTPException(status_code=409, detail="This turn is already being processed.")

        interview = await db.get(Interview, session.interview_id)
        media_type = "video" if interview.mode == "Video" else "audio"

        if existing is None:
            turn_row = InterviewTurn(
                session_id=session.id, turn_index=turn_index, status="pending", media_type=media_type
            )
            db.add(turn_row)
        else:  # existing.status == "failed" — retry allowed
            turn_row = existing
            turn_row.status = "pending"
            turn_row.error = None
        await db.commit()
        turn_row_id = turn_row.id

        prior_turns = (
            await db.execute(
                select(InterviewTurn)
                .where(
                    InterviewTurn.session_id == session.id,
                    InterviewTurn.turn_index < turn_index,
                    InterviewTurn.status == "complete",
                )
                .order_by(InterviewTurn.turn_index)
            )
        ).scalars().all()

        job = await db.get(Job, interview.job_id) if interview.job_id else None
        history = _reconstruct_history(interview, job, prior_turns)
        history = bound_history(history, settings.interview_history_max_turns)

    # Phase 2 — the slow cascade call, no DB session open.
    audio_bytes = await audio.read()
    try:
        result = await run_turn(history, audio_bytes, audio_format=audio_format)
    except LLMError as e:
        async with async_session() as db:
            turn_row = await db.get(InterviewTurn, turn_row_id)
            turn_row.status = "failed"
            turn_row.error = str(e)
            await db.commit()
        raise HTTPException(status_code=502, detail=f"Interview turn failed — please retry. ({e})")

    candidate_audio_path = save_interview_audio(
        audio_bytes, f"turn_{turn_index}_candidate.{audio_format}", session.id
    )
    ai_audio_path = save_interview_audio(result.ai_audio, f"turn_{turn_index}_ai.mp3", session.id)

    # Phase 3 — short session: persist the result and, if the interviewer signaled the end,
    # advance the session's own status.
    async with async_session() as db:
        turn_row = await db.get(InterviewTurn, turn_row_id)
        turn_row.status = "complete"
        turn_row.transcript = result.transcript
        turn_row.ai_text = result.ai_text
        turn_row.candidate_audio_path = str(candidate_audio_path)
        turn_row.candidate_audio_format = audio_format
        turn_row.ai_audio_path = str(ai_audio_path)
        turn_row.completed_at = datetime.now(timezone.utc)

        session_row = await db.get(InterviewSession, session.id)
        if result.is_complete:
            session_row.status = "complete"
            session_row.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return TurnResultView(
            sessionId=str(session.id),
            turnIndex=turn_index,
            transcript=result.transcript,
            aiText=result.ai_text,
            aiAudio=base64.b64encode(result.ai_audio).decode(),
            aiAudioFormat="mp3",
            status=session_row.status,
        )


@router.get("/interview-sessions/{session_id}", response_model=InterviewSessionView)
async def get_interview_session(
    session: InterviewSession = Depends(get_current_interview_session),
    db: AsyncSession = Depends(get_db),
):
    turns = (
        await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session.id).order_by(InterviewTurn.turn_index)
        )
    ).scalars().all()
    return InterviewSessionView(
        id=str(session.id),
        interviewId=str(session.interview_id),
        status=session.status,
        turns=_turn_summaries(turns),
    )


@router.post("/interview-sessions/{session_id}/complete", response_model=InterviewSessionView)
async def complete_interview_session(
    session: InterviewSession = Depends(get_current_interview_session),
    db: AsyncSession = Depends(get_db),
):
    """Explicit candidate-initiated end (bail early, before the interviewer's own
    [INTERVIEW_COMPLETE] sentinel would have fired). No-ops if already complete/abandoned."""
    if session.status == "active":
        session.status = "complete"
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)
    turns = (
        await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session.id).order_by(InterviewTurn.turn_index)
        )
    ).scalars().all()
    return InterviewSessionView(
        id=str(session.id),
        interviewId=str(session.interview_id),
        status=session.status,
        turns=_turn_summaries(turns),
    )
