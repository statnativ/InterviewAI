"""M4: interview-sessions tests — wiring the STT->LLM->TTS cascade into the app.

chat_completion/transcribe/synthesize are monkeypatched at
app.services.interview_pipeline's import site (same convention as
test_candidate_judge.py/test_question_generation.py) so no real OpenRouter
call happens. These tests exercise the router's persistence/idempotency
logic, not HTTP-layer resilience (that's test_ai_client_resilience.py's job).

Session/turn endpoints deliberately send NO tenant/user headers — that's the
point of the design (ADR-008): interview_sessions.id is the only credential.
Job/Interview setup still goes through the normal recruiter-side API with
headers, since that part of the app is unchanged.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

import app.routers.interview_sessions as interview_sessions_router
import app.services.interview_pipeline as interview_pipeline
from app.config import settings
from app.db import async_session
from app.deps import SEED_USER_EMAIL
from app.main import app
from app.models.interview_turn import InterviewTurn
from app.models.tenant import Tenant
from app.models.user import User
from app.services.llm_client import LLMError

pytestmark = pytest.mark.asyncio(loop_scope="session")

QUESTIONS = [
    {"prompt": "Tell me about a time you led a migration project.", "type": "Technical", "difficulty": "Medium"},
    {"prompt": "How do you handle a disagreement with a teammate?", "type": "Behavioral", "difficulty": "Easy"},
]


def _fake_chat_completion(response_text: str = "Tell me about your experience.", captured: list | None = None):
    async def fake(messages, model=None, exclude_reasoning=False, fallback_model=None):
        if captured is not None:
            captured.append(messages)
        return response_text

    return fake


async def _fake_transcribe(audio_bytes: bytes, audio_format: str = "wav") -> str:
    return "This is what the candidate said."


async def _fake_synthesize(text: str, voice: str | None = None) -> bytes:
    return b"fake-mp3-bytes"


@pytest.fixture(autouse=True)
def no_real_celery(monkeypatch):
    """M5: several tests here complete a session, which now enqueues an evaluation task
    (app/routers/interview_sessions.py's _trigger_evaluation) — never hit a real broker in
    this file's tests, that's test_interview_evaluation.py's job."""

    class FakeTask:
        delay = staticmethod(lambda session_id: None)

    monkeypatch.setattr(interview_sessions_router, "evaluate_interview_task", FakeTask())


@pytest.fixture
def cascade(monkeypatch):
    """Installs working fakes for all three legs; returns a dict of setters so
    individual tests can override one leg's behavior (e.g. raise, or return a
    specific captured-messages list)."""
    captured: list = []
    monkeypatch.setattr(interview_pipeline, "chat_completion", _fake_chat_completion(captured=captured))
    monkeypatch.setattr(interview_pipeline, "transcribe", _fake_transcribe)
    monkeypatch.setattr(interview_pipeline, "synthesize", _fake_synthesize)

    def set_llm_response(text: str):
        monkeypatch.setattr(interview_pipeline, "chat_completion", _fake_chat_completion(text, captured))

    def set_llm_raises():
        async def raiser(*args, **kwargs):
            raise LLMError("simulated LLM failure")

        monkeypatch.setattr(interview_pipeline, "chat_completion", raiser)

    return {"captured": captured, "set_llm_response": set_llm_response, "set_llm_raises": set_llm_raises}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def tenant():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        t = Tenant(name="Session Test Co", slug=f"session-test-{suffix}")
        db.add(t)
        await db.commit()
        await db.refresh(t)
        db.add(User(tenant_id=t.id, email=SEED_USER_EMAIL, name="Session Test Recruiter", role="recruiter"))
        await db.commit()
    try:
        yield t
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == t.id))
            await db.commit()


def _headers(t: Tenant) -> dict[str, str]:
    return {"X-Tenant-Id": str(t.id)}


async def _make_job(client, tenant) -> str:
    res = await client.post(
        "/jobs",
        json={"title": "Senior Engineer", "description": "A role."},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _make_interview(client, tenant, mode: str = "Voice", questions=QUESTIONS, job_id: str | None = None) -> str:
    if job_id is None:
        job_id = await _make_job(client, tenant)
    res = await client.post(
        "/interviews",
        json={"title": "Screening", "jobTitle": "Senior Engineer", "jobId": job_id, "mode": mode, "questions": questions},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["id"]


def _audio_payload(turn_index: int, audio_format: str = "wav"):
    return (
        {"turn_index": str(turn_index), "audio_format": audio_format},
        {"audio": ("answer.wav", b"fake-candidate-audio-bytes", "audio/wav")},
    )


async def test_create_session_happy_path(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    res = await client.post(f"/interviews/{interview_id}/sessions")
    assert res.status_code == 201
    body = res.json()
    assert body["turnIndex"] == 0
    assert body["transcript"] is None
    assert body["aiText"] == "Tell me about your experience."
    assert body["aiAudio"]  # non-empty base64
    assert body["status"] == "active"
    assert uuid.UUID(body["sessionId"])


async def test_create_session_requires_voice_or_video_mode(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant, mode="Chat")
    res = await client.post(f"/interviews/{interview_id}/sessions")
    assert res.status_code == 400


async def test_create_session_requires_questions(client, tenant, cascade):
    # No jobId, so create_interview's auto-generate-if-empty path never triggers —
    # this is the only way to get a genuinely empty `questions` on the row.
    res = await client.post(
        "/interviews",
        json={"title": "Screening", "jobTitle": "Senior Engineer", "mode": "Voice", "questions": []},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    interview_id = res.json()["id"]

    session_res = await client.post(f"/interviews/{interview_id}/sessions")
    assert session_res.status_code == 400


async def test_create_session_unknown_interview_is_404(client, cascade):
    res = await client.post(f"/interviews/{uuid.uuid4()}/sessions")
    assert res.status_code == 404


async def test_turn_happy_path_no_tenant_headers_needed(client, tenant, cascade):
    """The whole point of the design: this call sends zero identifying headers
    and still works, scoped only by the unguessable session_id."""
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    data, files = _audio_payload(1)
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["turnIndex"] == 1
    assert body["transcript"] == "This is what the candidate said."
    assert body["status"] == "active"


async def test_turn_idempotent_retry_returns_cached_result_not_rerun(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    data, files = _audio_payload(1)
    first = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert first.status_code == 200

    calls_after_first = len(cascade["captured"])

    data, files = _audio_payload(1)  # same turn_index — a client-side retry
    second = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(cascade["captured"]) == calls_after_first  # cascade NOT called again


async def test_turn_while_pending_is_409(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    # Simulate a request for this exact turn already in flight.
    async with async_session() as db:
        db.add(InterviewTurn(session_id=uuid.UUID(session_id), turn_index=1, status="pending"))
        await db.commit()

    data, files = _audio_payload(1)
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 409


async def test_turn_failure_marks_row_failed_and_allows_retry(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    cascade["set_llm_raises"]()
    data, files = _audio_payload(1)
    failed = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert failed.status_code == 502

    async with async_session() as db:
        turn = (
            await db.execute(
                select(InterviewTurn).where(
                    InterviewTurn.session_id == uuid.UUID(session_id), InterviewTurn.turn_index == 1
                )
            )
        ).scalar_one()
        assert turn.status == "failed"
        assert turn.error

    # Session should still be active — the candidate can retry the same turn.
    still_active = await client.get(f"/interview-sessions/{session_id}")
    assert still_active.json()["status"] == "active"

    cascade["set_llm_response"]("Good, next question.")
    data, files = _audio_payload(1)
    retried = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert retried.status_code == 200
    assert retried.json()["status"] == "active"


async def test_unknown_session_id_is_404(client, cascade):
    res = await client.get(f"/interview-sessions/{uuid.uuid4()}")
    assert res.status_code == 404


async def test_turn_on_completed_session_is_409(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]
    await client.post(f"/interview-sessions/{session_id}/complete")

    data, files = _audio_payload(1)
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 409


async def test_history_bounding_caps_messages_sent_to_llm(client, tenant, cascade, monkeypatch):
    monkeypatch.setattr(settings, "interview_history_max_turns", 2)
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    for i in range(1, 5):
        cascade["set_llm_response"](f"Follow-up question {i}.")
        data, files = _audio_payload(i)
        res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
        assert res.status_code == 200

    # The last captured call's history should be system prompt + at most 2 prior messages.
    last_history = cascade["captured"][-1]
    assert len(last_history) <= 1 + 2 + 1  # system + bounded 2 + this turn's new user message
    assert last_history[0]["role"] == "system"


async def test_completion_sentinel_ends_session_and_is_stripped(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant)
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    cascade["set_llm_response"]("Thanks for your time! [INTERVIEW_COMPLETE]")
    data, files = _audio_payload(1)
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 200
    body = res.json()
    assert "[INTERVIEW_COMPLETE]" not in body["aiText"]
    assert body["aiText"] == "Thanks for your time!"
    assert body["status"] == "complete"

    fetched = await client.get(f"/interview-sessions/{session_id}")
    assert fetched.json()["status"] == "complete"


async def test_create_session_video_mode(client, tenant, cascade):
    """M4b: Video mode uses the exact same session-creation path as Voice — no cascade
    changes needed, only the mode gate."""
    interview_id = await _make_interview(client, tenant, mode="Video")
    res = await client.post(f"/interviews/{interview_id}/sessions")
    assert res.status_code == 201

    session_id = res.json()["sessionId"]
    fetched = await client.get(f"/interview-sessions/{session_id}")
    assert fetched.json()["turns"][0]["mediaType"] == "video"


async def test_video_mode_turn_persists_media_type(client, tenant, cascade):
    interview_id = await _make_interview(client, tenant, mode="Video")
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    data = {"turn_index": "1", "audio_format": "webm"}
    files = {"audio": ("answer.webm", b"fake-candidate-video-bytes", "video/webm")}
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 200

    fetched = await client.get(f"/interview-sessions/{session_id}")
    turn_1 = next(t for t in fetched.json()["turns"] if t["turnIndex"] == 1)
    assert turn_1["mediaType"] == "video"


async def test_voice_mode_turn_media_type_stays_audio(client, tenant, cascade):
    """Regression: adding Video mode must not change Voice mode's existing behavior."""
    interview_id = await _make_interview(client, tenant, mode="Voice")
    session_id = (await client.post(f"/interviews/{interview_id}/sessions")).json()["sessionId"]

    data, files = _audio_payload(1)
    res = await client.post(f"/interview-sessions/{session_id}/turns", data=data, files=files)
    assert res.status_code == 200

    fetched = await client.get(f"/interview-sessions/{session_id}")
    for turn in fetched.json()["turns"]:
        assert turn["mediaType"] == "audio"
