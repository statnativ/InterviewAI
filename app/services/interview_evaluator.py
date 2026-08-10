"""LLM-as-judge for a completed interview transcript (M5).

Pattern-matches candidate_judge.py deliberately closely: one chat_completion
call, prompt asks for JSON only, strip markdown fences, json.loads, no
silent partial fallback on a malformed response. The only real difference
is the input — a transcript instead of a résumé profile — scored against
the same Job.rubric shape candidate_judge.py already uses, per the decision
to evaluate the whole interview at once rather than inventing a new
per-question rubric concept.

evaluate_interview() is meant to be called from inside a Celery task
(app/celery_app.py), not directly from a router — it uses the app's shared
app.db.async_session rather than opening its own engine, which only works
because the Celery worker process keeps one persistent event loop alive for
its whole lifetime (see app/celery_app.py's worker_process_init signal and
ADR-009) — the same loop app.db's module-level engine and
llm_client.get_http_client()'s shared httpx.AsyncClient both get bound to on
first use. A naive fresh-engine-per-task or asyncio.run()-per-task approach
would NOT be safe here for exactly that reason.

Never raises out of evaluate_interview() — any failure (missing job/rubric,
malformed LLM output, a DB error) is caught and persisted as
evaluation_status="failed" + evaluation_error, matching
_run_judge_in_background's reasoning: once this runs inside a Celery task,
there's no HTTP response left to surface a failure through, so silence
would strand the row at "pending" forever.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy import select

from app.db import async_session
from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.job import Job
from app.services.llm_client import LLMError, chat_completion
from app.services.llm_scoring import clamp_int, coerce_scorecard, strip_fences
from app.services.screening import RubricCriterion, ScorecardRow


class EvalResult(TypedDict):
    score: int
    scorecard: list[ScorecardRow]
    ai_note: str
    ai_verdict: str
    strengths: list[str]
    gaps: list[str]


EVAL_PROMPT = """You are an expert technical interviewer evaluating a candidate's completed \
live interview transcript against a job's rubric. Return ONLY a valid JSON object (no markdown \
fences, no commentary) shaped exactly like:

{{"score": int (0-99), "ai_verdict": "Advance" | "Maybe" | "Pass", "ai_note": string, \
"strengths": [string, ...], "gaps": [string, ...], \
"scorecard": [{{"criterion": string, "score": int (0-100), "note": string}}, ...]}}

Score each rubric criterion below on its own merits — reason about the depth, specificity, and \
correctness of what the candidate actually said in the transcript, not just whether they \
mentioned a relevant keyword. Include exactly one scorecard entry per rubric criterion listed \
below, using the criterion's exact label. The top-level "score" should reflect overall interview \
performance, weighted toward Must-have criteria over Nice-to-have ones.

Job title: {job_title}
Job description:
---
{job_description}
---
Rubric (label — tag — weight%):
{rubric_block}

Interview transcript (Interviewer asks, Candidate answers):
---
{transcript_block}
---
"""


def _coerce_result(parsed: dict, rubric: list[RubricCriterion]) -> EvalResult:
    score = clamp_int(parsed.get("score"), 0, 99)

    verdict = parsed.get("ai_verdict")
    if verdict not in ("Advance", "Maybe", "Pass"):
        verdict = "Advance" if score >= 80 else "Maybe" if score >= 55 else "Pass"

    scorecard = coerce_scorecard(rubric, parsed.get("scorecard"), source_label="AI-evaluated")

    ai_note = str(parsed.get("ai_note", "")).strip() or f"Interview evaluation score {score}/100."
    strengths = [str(s) for s in parsed.get("strengths", [])] if isinstance(parsed.get("strengths"), list) else []
    gaps = [str(g) for g in parsed.get("gaps", [])] if isinstance(parsed.get("gaps"), list) else []

    return {
        "score": score,
        "scorecard": scorecard,
        "ai_note": ai_note,
        "ai_verdict": verdict,
        "strengths": strengths,
        "gaps": gaps,
    }


def _build_transcript(turns: list[InterviewTurn]) -> str:
    """Same conceptual ordering as interview_sessions.py's _reconstruct_history — turn 0's
    ai_text is the opening question, then each subsequent turn's transcript answers the
    PREVIOUS turn's question and its own ai_text is the next question/follow-up. Re-implemented
    locally rather than importing that router's private helper (service layer shouldn't depend
    on a router module). Only complete turns are included — a failed turn the candidate
    successfully retried leaves no gap (the retry's row is what's persisted as complete)."""
    lines: list[str] = []
    for turn in turns:
        if turn.turn_index == 0:
            lines.append(f"Interviewer: {turn.ai_text}")
        else:
            lines.append(f"Candidate: {turn.transcript}")
            if turn.ai_text:
                lines.append(f"Interviewer: {turn.ai_text}")
    return "\n".join(lines)


async def _mark_failed(session_id: uuid.UUID, error: str) -> None:
    async with async_session() as db:
        session = await db.get(InterviewSession, session_id)
        if session is None:
            return
        session.evaluation_status = "failed"
        session.evaluation_error = error
        await db.commit()


async def evaluate_interview(session_id: uuid.UUID) -> None:
    try:
        async with async_session() as db:
            session = await db.get(InterviewSession, session_id)
            if session is None:
                return

            turns = (
                await db.execute(
                    select(InterviewTurn)
                    .where(InterviewTurn.session_id == session_id, InterviewTurn.status == "complete")
                    .order_by(InterviewTurn.turn_index)
                )
            ).scalars().all()

            interview = await db.get(Interview, session.interview_id)
            job = await db.get(Job, interview.job_id) if interview and interview.job_id else None

            if job is None or not job.rubric:
                session.evaluation_status = "failed"
                session.evaluation_error = (
                    "No linked job/rubric — evaluation requires a job-linked interview."
                )
                await db.commit()
                return

            transcript_block = _build_transcript(list(turns))
            rubric_block = "\n".join(f"- {r['label']} — {r['tag']} — {r['weight']}%" for r in job.rubric)
            prompt = EVAL_PROMPT.format(
                job_title=job.title,
                job_description=job.description,
                rubric_block=rubric_block,
                transcript_block=transcript_block,
            )

        # LLM call outside the DB session, same phasing discipline as interview_sessions.py's
        # submit_turn (no DB session held open across a slow external call).
        raw = await chat_completion([{"role": "user", "content": prompt}])
        try:
            parsed = json.loads(strip_fences(raw))
        except json.JSONDecodeError as e:
            raise LLMError(f"Evaluation returned invalid JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise LLMError("Evaluation did not return a single JSON object")

        result = _coerce_result(parsed, job.rubric)

        async with async_session() as db:
            session = await db.get(InterviewSession, session_id)
            session.score = result["score"]
            session.scorecard = result["scorecard"]
            session.strengths = result["strengths"]
            session.gaps = result["gaps"]
            session.ai_verdict = result["ai_verdict"]
            session.ai_note = result["ai_note"]
            session.evaluation_status = "complete"
            session.evaluation_error = None
            session.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as e:  # noqa: BLE001 — broad on purpose, see module docstring
        await _mark_failed(session_id, str(e))
