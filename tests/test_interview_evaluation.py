"""M5: interview evaluation — evaluate_interview() service directly, plus the
recruiter-facing report/decision/evaluate/media endpoints in
app/routers/interview_reports.py.

chat_completion is monkeypatched at app.services.interview_evaluator's import
site (same convention as test_interview_sessions.py/test_candidate_judge.py)
— no real OpenRouter call. evaluate_interview_task.delay is monkeypatched at
both app.routers.interview_sessions's and app.routers.interview_reports's
import sites so nothing ever tries to reach a real Redis broker in tests.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

import app.routers.interview_reports as interview_reports
import app.routers.interview_sessions as interview_sessions_router
import app.services.interview_evaluator as interview_evaluator
import app.services.interview_pipeline as interview_pipeline
from app.db import async_session
from app.deps import SEED_USER_EMAIL
from app.main import app
from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.tenant import Tenant
from app.models.user import User
from app.services.llm_client import LLMError

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def no_real_celery(monkeypatch):
    """Neither router should ever hit a real broker in tests — captures calls instead."""
    calls: list[str] = []

    def fake_delay(session_id: str):
        calls.append(session_id)

    class FakeTask:
        delay = staticmethod(fake_delay)

    monkeypatch.setattr(interview_sessions_router, "evaluate_interview_task", FakeTask())
    monkeypatch.setattr(interview_reports, "evaluate_interview_task", FakeTask())
    return calls


@pytest.fixture(autouse=True)
def cascade(monkeypatch):
    """Only test_interview_sessions.py's own file needs a rich, per-test-overridable version
    of this — here it just needs to not hit the real OpenRouter API for the couple of tests
    that call POST /interviews/{id}/sessions (which itself calls interview_pipeline.start_interview)."""
    async def fake_chat_completion(messages, model=None, exclude_reasoning=False, fallback_model=None):
        return "Tell me about your experience."

    async def fake_synthesize(text: str, voice: str | None = None) -> bytes:
        return b"fake-mp3-bytes"

    monkeypatch.setattr(interview_pipeline, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(interview_pipeline, "synthesize", fake_synthesize)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def tenant():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        t = Tenant(name="Eval Test Co", slug=f"eval-test-{suffix}")
        db.add(t)
        await db.commit()
        await db.refresh(t)
        db.add(User(tenant_id=t.id, email=SEED_USER_EMAIL, name="Eval Test Recruiter", role="recruiter"))
        await db.commit()
    try:
        yield t
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == t.id))
            await db.commit()


def _headers(t: Tenant) -> dict[str, str]:
    return {"X-Tenant-Id": str(t.id)}


async def _make_job(client, tenant) -> dict:
    res = await client.post(
        "/jobs",
        json={"title": "Senior Engineer", "description": "Backend role, Python and distributed systems."},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()


async def _make_interview(client, tenant, job: dict | None = None, mode: str = "Voice") -> str:
    if job is None:
        job = await _make_job(client, tenant)
    res = await client.post(
        "/interviews",
        json={
            "title": "Screening",
            "jobTitle": job["title"],
            "jobId": job["id"],
            "mode": mode,
            "questions": [{"prompt": "Tell me about your experience.", "type": "Technical", "difficulty": "Medium"}],
        },
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _make_session_with_turns(client, tenant, job: dict | None = None) -> tuple[str, str]:
    """Bypasses the real cascade — inserts a session + a couple of complete turns directly,
    matching test_interview_sessions.py's test_turn_while_pending_is_409 precedent for
    constructing turn rows straight in the DB rather than through the mocked pipeline."""
    interview_id = await _make_interview(client, tenant, job=job)
    async with async_session() as db:
        interview = await db.get(Interview, uuid.UUID(interview_id))
        session = InterviewSession(
            tenant_id=interview.tenant_id, interview_id=interview.id, status="complete", evaluation_status="idle",
        )
        db.add(session)
        await db.flush()
        db.add(InterviewTurn(
            session_id=session.id, turn_index=0, status="complete", media_type="audio",
            ai_text="Tell me about your experience.",
        ))
        db.add(InterviewTurn(
            session_id=session.id, turn_index=1, status="complete", media_type="audio",
            transcript="I led a migration project at my last job.",
            ai_text="What was the hardest part?",
            candidate_audio_path=None, candidate_audio_format=None,
        ))
        await db.commit()
        session_id = str(session.id)
    return interview_id, session_id


def _fake_eval_response(rubric: list[dict], score: int = 82):
    async def fake(messages, model=None, exclude_reasoning=False, fallback_model=None):
        import json
        scorecard = [{"criterion": r["label"], "score": 80, "note": "Solid answer."} for r in rubric]
        return json.dumps({
            "score": score, "ai_verdict": "Advance", "ai_note": "Strong technical depth.",
            "strengths": ["Clear communication"], "gaps": ["Limited testing detail"],
            "scorecard": scorecard,
        })
    return fake


# --- evaluate_interview() service, direct ---

async def test_evaluate_interview_success(client, tenant, monkeypatch):
    job = await _make_job(client, tenant)
    _, session_id = await _make_session_with_turns(client, tenant, job=job)

    monkeypatch.setattr(interview_evaluator, "chat_completion", _fake_eval_response(job["rubric"]))
    await interview_evaluator.evaluate_interview(uuid.UUID(session_id))

    async with async_session() as db:
        session = await db.get(InterviewSession, uuid.UUID(session_id))
        assert session.evaluation_status == "complete"
        assert session.score == 82
        assert session.ai_verdict == "Advance"
        assert len(session.scorecard) == len(job["rubric"])
        assert session.strengths == ["Clear communication"]
        assert session.evaluated_at is not None


async def test_evaluate_interview_no_job_fails_cleanly(client, tenant, monkeypatch):
    # An interview created with no jobId has nothing to evaluate against.
    res = await client.post(
        "/interviews",
        json={"title": "Generic", "jobTitle": "Generic Role", "mode": "Voice",
              "questions": [{"prompt": "Tell me about yourself.", "type": "Behavioral", "difficulty": "Easy"}]},
        headers=_headers(tenant),
    )
    interview_id = res.json()["id"]
    async with async_session() as db:
        interview = await db.get(Interview, uuid.UUID(interview_id))
        session = InterviewSession(tenant_id=interview.tenant_id, interview_id=interview.id, status="complete")
        db.add(session)
        await db.flush()
        db.add(InterviewTurn(session_id=session.id, turn_index=0, status="complete", ai_text="Hi."))
        await db.commit()
        session_id = session.id

    monkeypatch.setattr(interview_evaluator, "chat_completion", _fake_eval_response([]))
    await interview_evaluator.evaluate_interview(session_id)

    async with async_session() as db:
        session = await db.get(InterviewSession, session_id)
        assert session.evaluation_status == "failed"
        assert "rubric" in session.evaluation_error.lower() or "job" in session.evaluation_error.lower()


async def test_evaluate_interview_malformed_response_fails_cleanly(client, tenant, monkeypatch):
    job = await _make_job(client, tenant)
    _, session_id = await _make_session_with_turns(client, tenant, job=job)

    async def bad_response(messages, model=None, exclude_reasoning=False, fallback_model=None):
        return "not valid json at all"

    monkeypatch.setattr(interview_evaluator, "chat_completion", bad_response)
    await interview_evaluator.evaluate_interview(uuid.UUID(session_id))

    async with async_session() as db:
        session = await db.get(InterviewSession, uuid.UUID(session_id))
        assert session.evaluation_status == "failed"
        assert session.evaluation_error


# --- trigger wiring (interview_sessions.py) ---

async def test_complete_endpoint_sets_pending_and_enqueues(client, tenant, no_real_celery):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]
    res = await client.post(f"/interview-sessions/{session_id}/complete")
    assert res.status_code == 200

    async with async_session() as db:
        session = await db.get(InterviewSession, uuid.UUID(session_id))
        assert session.evaluation_status == "pending"
    assert session_id in no_real_celery


# --- interview_reports.py router ---

async def test_list_and_get_report(client, tenant):
    job = await _make_job(client, tenant)
    interview_id, session_id = await _make_session_with_turns(client, tenant, job=job)

    listing = await client.get(f"/interviews/{interview_id}/sessions", headers=_headers(tenant))
    assert listing.status_code == 200
    assert any(s["id"] == session_id for s in listing.json())

    report = await client.get(f"/interview-sessions/{session_id}/report", headers=_headers(tenant))
    assert report.status_code == 200
    body = report.json()
    assert body["id"] == session_id
    assert len(body["turns"]) == 2
    assert body["decision"] == "None"


async def test_report_wrong_tenant_is_404(client, tenant):
    _, session_id = await _make_session_with_turns(client, tenant)

    other_suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        other = Tenant(name="Other Co", slug=f"other-{other_suffix}")
        db.add(other)
        await db.commit()
        await db.refresh(other)
        db.add(User(tenant_id=other.id, email=SEED_USER_EMAIL, name="Other Recruiter", role="recruiter"))
        await db.commit()

    res = await client.get(f"/interview-sessions/{session_id}/report", headers=_headers(other))
    assert res.status_code == 404

    async with async_session() as db:
        await db.execute(delete(Tenant).where(Tenant.id == other.id))
        await db.commit()


async def test_patch_decision_never_touches_ai_fields(client, tenant):
    job = await _make_job(client, tenant)
    _, session_id = await _make_session_with_turns(client, tenant, job=job)

    async with async_session() as db:
        session = await db.get(InterviewSession, uuid.UUID(session_id))
        session.score = 91
        session.ai_verdict = "Advance"
        await db.commit()

    res = await client.patch(
        f"/interview-sessions/{session_id}", json={"decision": "Approved"}, headers=_headers(tenant)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "Approved"
    assert body["score"] == 91  # untouched
    assert body["aiVerdict"] == "Advance"  # untouched


async def test_retry_evaluate_guards(client, tenant, no_real_celery):
    job = await _make_job(client, tenant)
    _, session_id = await _make_session_with_turns(client, tenant, job=job)

    ok = await client.post(f"/interview-sessions/{session_id}/evaluate", headers=_headers(tenant))
    assert ok.status_code == 202
    assert session_id in no_real_celery

    # Already pending — a second call is a 409.
    again = await client.post(f"/interview-sessions/{session_id}/evaluate", headers=_headers(tenant))
    assert again.status_code == 409


async def test_evaluate_not_complete_session_is_400(client, tenant):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]  # still active

    res = await client.post(f"/interview-sessions/{session_id}/evaluate", headers=_headers(tenant))
    assert res.status_code == 400


async def test_media_404_on_missing_path_and_turn(client, tenant):
    _, session_id = await _make_session_with_turns(client, tenant)

    # Turn 0 has no candidate audio at all.
    no_candidate = await client.get(
        f"/interview-sessions/{session_id}/turns/0/media", params={"speaker": "candidate"}, headers=_headers(tenant)
    )
    assert no_candidate.status_code == 404

    out_of_range = await client.get(
        f"/interview-sessions/{session_id}/turns/99/media", params={"speaker": "ai"}, headers=_headers(tenant)
    )
    assert out_of_range.status_code == 404
