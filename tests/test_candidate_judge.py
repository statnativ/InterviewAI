"""M2 (LLM-as-judge candidate scoring) + IA-003 (off the request path) tests.

Same conventions as test_question_generation.py: chat_completion is
monkeypatched at candidate_judge's import site so the real OpenRouter call
never happens; a real dev-DB tenant/job/candidate is created and cleaned up
per test.

IA-003: POST /candidates/{id}/judge now returns 202 and runs the LLM call via
FastAPI BackgroundTasks — success/failure surfaces via polling
GET /candidates/{id}, not the POST response. _poll_until_not_pending is the
test-side equivalent of the frontend's polling loop.
"""
import asyncio
import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

import app.routers.candidates as candidates_router
import app.services.candidate_judge as candidate_judge
from app.db import async_session
from app.deps import SEED_USER_EMAIL
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

CANNED_SCORECARD = [
    # "We need a strong Go and PostgreSQL engineer." also extracts "SQL" as its
    # own skill-dictionary hit (a substring of PostgreSQL) — every rubric
    # criterion needs a matching row or the judge correctly rejects the
    # response as incomplete, so all three must be covered here.
    {"criterion": "Go", "score": 90, "note": "Led a production Go migration."},
    {"criterion": "PostgreSQL", "score": 70, "note": "Used PostgreSQL as a secondary datastore."},
    {"criterion": "SQL", "score": 75, "note": "Comfortable writing complex SQL."},
]


def _canned_judge_response(scorecard=None):
    return json.dumps(
        {
            "score": 82,
            "compare_verdict": "Advance",
            "ai_note": "Strong backend fit, reasoned from actual project depth.",
            "strengths": ["Deep Go experience", "Led a real migration project"],
            "gaps": ["Limited PostgreSQL depth"],
            "scorecard": scorecard if scorecard is not None else CANNED_SCORECARD,
        }
    )


def _fake_chat_completion(response_text: str, captured: list | None = None):
    async def fake(messages, model=None, exclude_reasoning=False, fallback_model=None):
        if captured is not None:
            captured.append(messages[0]["content"])
        return response_text

    return fake


@pytest.fixture
def judge_response(monkeypatch):
    def _install(response_text: str, captured: list | None = None):
        monkeypatch.setattr(candidate_judge, "chat_completion", _fake_chat_completion(response_text, captured))

    return _install


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def tenant():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        t = Tenant(name="Judge Test Co", slug=f"judge-test-{suffix}")
        db.add(t)
        await db.commit()
        await db.refresh(t)
        db.add(User(tenant_id=t.id, email=SEED_USER_EMAIL, name="Judge Test Recruiter", role="recruiter"))
        await db.commit()
    try:
        yield t
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == t.id))
            await db.commit()


def _headers(t: Tenant) -> dict[str, str]:
    return {"X-Tenant-Id": str(t.id)}


async def _make_job(client, tenant, description="We need a strong Go and PostgreSQL engineer.") -> str:
    res = await client.post(
        "/jobs",
        json={"title": "Senior Go Engineer", "description": description},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _make_candidate(client, tenant, job_id: str) -> dict:
    res = await client.post(
        "/candidates",
        json={
            "jobId": job_id,
            "name": "Jordan Rivera",
            "email": "jordan.rivera@example.com",
            "resumeText": "Led the Kafka migration at Acme. Strong in Go, PostgreSQL, Kubernetes.",
        },
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["candidate"]


async def _poll_until_not_pending(client, tenant, candidate_id: str, timeout: float = 5.0) -> dict:
    """Test-side equivalent of the frontend's polling loop. chat_completion is
    mocked, so the background task resolves almost immediately regardless of
    whether ASGITransport happens to run BackgroundTasks inline or truly
    deferred — this doesn't assume either way, it just polls."""
    elapsed = 0.0
    interval = 0.02
    while elapsed < timeout:
        res = await client.get(f"/candidates/{candidate_id}", headers=_headers(tenant))
        body = res.json()
        if body["judgeStatus"] != "pending":
            return body
        await asyncio.sleep(interval)
        elapsed += interval
    raise AssertionError(f"judgeStatus still 'pending' after {timeout}s — background task never completed")


async def test_judge_returns_202_and_completes_via_polling(client, tenant, judge_response):
    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)
    judge_response(_canned_judge_response())

    res = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert res.status_code == 202
    assert res.json()["judgeStatus"] == "pending"

    body = await _poll_until_not_pending(client, tenant, candidate["id"])

    assert body["judgeStatus"] == "idle"
    assert body["scoreMethod"] == "llm_judge"
    assert body["score"] == 82
    assert body["compareVerdict"] == "Advance"
    assert body["shortlisted"] is True  # score >= 80, computed server-side
    assert body["strengths"] == ["Deep Go experience", "Led a real migration project"]
    assert body["gaps"] == ["Limited PostgreSQL depth"]
    assert body["aiNote"] == "Strong backend fit, reasoned from actual project depth."

    scorecard = {row["criterion"]: row for row in body["scorecard"]}
    assert set(scorecard) == {"Go", "PostgreSQL", "SQL"}
    assert scorecard["Go"]["score"] == 90
    # weight comes from the rubric, never the LLM's output
    job = await client.get(f"/jobs/{job_id}", headers=_headers(tenant))
    rubric_weights = {r["label"]: r["weight"] for r in job.json()["rubric"]}
    assert scorecard["Go"]["weight"] == rubric_weights["Go"]


async def test_malformed_llm_output_sets_failed_status_and_leaves_row_untouched(client, tenant, judge_response):
    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)
    before = candidate.copy()

    judge_response("not json at all")
    res = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert res.status_code == 202

    body = await _poll_until_not_pending(client, tenant, candidate["id"])
    assert body["judgeStatus"] == "failed"
    assert body["judgeError"]
    assert body["scoreMethod"] == "deterministic"
    assert body["score"] == before["score"]
    assert body["scorecard"] == before["scorecard"]


async def test_llm_output_missing_a_rubric_criterion_sets_failed_status(client, tenant, judge_response):
    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)
    # Only one of the three rubric criteria covered.
    judge_response(_canned_judge_response(scorecard=[CANNED_SCORECARD[0]]))

    res = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert res.status_code == 202

    body = await _poll_until_not_pending(client, tenant, candidate["id"])
    assert body["judgeStatus"] == "failed"
    assert body["scoreMethod"] == "deterministic"


async def test_judge_while_already_pending_is_409(client, tenant, monkeypatch):
    async def hang(*args, **kwargs):
        return None  # deliberately never resolves judge_status off "pending"

    monkeypatch.setattr(candidates_router, "_run_judge_in_background", hang)

    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)

    first = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert first.status_code == 202
    assert first.json()["judgeStatus"] == "pending"

    second = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert second.status_code == 409


async def test_candidate_creation_never_calls_the_judge(client, tenant, monkeypatch):
    async def explode(*args, **kwargs):
        raise AssertionError("judge_candidate should never be called from candidate creation")

    monkeypatch.setattr(candidate_judge, "chat_completion", explode)

    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)
    assert candidate["scoreMethod"] == "deterministic"
    assert candidate["judgeStatus"] == "idle"


async def test_judge_requires_a_rubric(client, tenant, judge_response):
    res = await client.post(
        "/jobs", json={"title": "No Rubric Role", "description": ""}, headers=_headers(tenant)
    )
    job_id = res.json()["id"]
    candidate = await _make_candidate(client, tenant, job_id)

    judge_response(_canned_judge_response())
    res = await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    assert res.status_code == 400


async def test_judge_is_tenant_scoped(client, tenant, judge_response):
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        other = Tenant(name="Other Judge Tenant", slug=f"judge-other-{suffix}")
        db.add(other)
        await db.commit()
        await db.refresh(other)
        db.add(User(tenant_id=other.id, email=SEED_USER_EMAIL, name="Other Recruiter", role="recruiter"))
        await db.commit()
    try:
        other_job_id = await _make_job(client, other)
        other_candidate = await _make_candidate(client, other, other_job_id)

        judge_response(_canned_judge_response())
        res = await client.post(f"/candidates/{other_candidate['id']}/judge", headers=_headers(tenant))
        assert res.status_code == 404
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == other.id))
            await db.commit()


async def test_screen_after_judge_reverts_to_deterministic(client, tenant, judge_response):
    job_id = await _make_job(client, tenant)
    candidate = await _make_candidate(client, tenant, job_id)

    judge_response(_canned_judge_response())
    await client.post(f"/candidates/{candidate['id']}/judge", headers=_headers(tenant))
    judged = await _poll_until_not_pending(client, tenant, candidate["id"])
    assert judged["scoreMethod"] == "llm_judge"

    rescreened = await client.post(f"/candidates/{candidate['id']}/screen", headers=_headers(tenant))
    assert rescreened.status_code == 200
    assert rescreened.json()["scoreMethod"] == "deterministic"
    assert rescreened.json()["score"] == candidate["score"]
