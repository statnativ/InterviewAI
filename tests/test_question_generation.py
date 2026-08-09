"""M3: AI question generation tests — the suite's first LLM-mocked tests.

chat_completion is monkeypatched at app.services.question_generator's import
site (not llm_client itself) so the real OpenRouter network call never
happens; the fake inspects the prompt to tell a "generate N questions" call
apart from a "regenerate one question" call, same as a real model would
respond differently to each.
"""
import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

import app.services.question_generator as question_generator
from app.db import async_session
from app.deps import SEED_USER_EMAIL
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

CANNED_QUESTIONS = [
    {"prompt": "Tell me about a time you used Go in production.", "type": "Technical", "difficulty": "Medium"},
    {"prompt": "How would you design a rate limiter?", "type": "System Design", "difficulty": "Hard"},
    {"prompt": "Describe a conflict with a teammate and how you resolved it.", "type": "Behavioral", "difficulty": "Easy"},
    {"prompt": "What engineering culture do you thrive in?", "type": "Culture", "difficulty": "Easy"},
    {"prompt": "Explain how you'd debug a memory leak in a Go service.", "type": "Technical", "difficulty": "Hard"},
    {"prompt": "Tell me about a migration project you led.", "type": "Technical", "difficulty": "Medium"},
    {"prompt": "How do you prioritize competing deadlines?", "type": "Behavioral", "difficulty": "Medium"},
    {"prompt": "Walk me through a production incident you led.", "type": "System Design", "difficulty": "Hard"},
]


def _fake_chat_completion(captured: list):
    async def fake(messages, model=None, exclude_reasoning=False):
        prompt = messages[0]["content"]
        captured.append(prompt)
        if "ONE replacement interview question" in prompt:
            return json.dumps({"prompt": "Regenerated question about debugging.", "type": "Technical", "difficulty": "Hard"})
        return json.dumps(CANNED_QUESTIONS)

    return fake


@pytest.fixture
def captured_prompts(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(question_generator, "chat_completion", _fake_chat_completion(captured))
    return captured


@pytest.fixture
def broken_llm(monkeypatch):
    async def fake(messages, model=None, exclude_reasoning=False):
        return "not json at all"

    monkeypatch.setattr(question_generator, "chat_completion", fake)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def tenant():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        t = Tenant(name="Question Gen Test Co", slug=f"qgen-test-{suffix}")
        db.add(t)
        await db.commit()
        await db.refresh(t)
        db.add(User(tenant_id=t.id, email=SEED_USER_EMAIL, name="QGen Test Recruiter", role="recruiter"))
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
        json={"title": "Senior Go Engineer", "description": "We need a strong Go and PostgreSQL engineer."},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _make_candidate(client, tenant, job_id: str) -> str:
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
    return res.json()["candidate"]["id"]


async def test_create_with_job_id_generates_questions(client, tenant, captured_prompts):
    job_id = await _make_job(client, tenant)
    res = await client.post(
        "/interviews",
        json={"title": "Go Engineer Screen", "jobTitle": "Senior Go Engineer", "jobId": job_id, "mode": "Chat"},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    body = res.json()
    assert 8 <= len(body["questions"]) <= 12
    assert body["jobId"] == job_id
    assert body["candidateId"] is None
    types = {q["type"] for q in body["questions"]}
    assert types <= {"Technical", "Behavioral", "System Design", "Culture"}


async def test_create_without_job_id_does_not_generate(client, tenant, captured_prompts):
    res = await client.post(
        "/interviews",
        json={"title": "Manual Interview", "jobTitle": "Whatever Role", "mode": "Chat"},
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    assert res.json()["questions"] == []
    assert captured_prompts == []


async def test_malformed_llm_output_is_a_clean_502(client, tenant, broken_llm):
    job_id = await _make_job(client, tenant)
    res = await client.post(
        "/interviews",
        json={"title": "Go Engineer Screen", "jobTitle": "Senior Go Engineer", "jobId": job_id, "mode": "Chat"},
        headers=_headers(tenant),
    )
    assert res.status_code == 502


async def test_regenerate_all_replaces_the_question_set(client, tenant, captured_prompts):
    job_id = await _make_job(client, tenant)
    created = await client.post(
        "/interviews",
        json={"title": "Go Engineer Screen", "jobTitle": "Senior Go Engineer", "jobId": job_id, "mode": "Chat"},
        headers=_headers(tenant),
    )
    iv_id = created.json()["id"]
    original_ids = {q["id"] for q in created.json()["questions"]}

    regenerated = await client.post(f"/interviews/{iv_id}/regenerate", headers=_headers(tenant))
    assert regenerated.status_code == 200
    new_ids = {q["id"] for q in regenerated.json()["questions"]}
    assert new_ids == original_ids  # same id scheme (q1..qN), content re-derived
    assert 8 <= len(regenerated.json()["questions"]) <= 12


async def test_regenerate_without_job_id_is_400(client, tenant):
    res = await client.post(
        "/interviews",
        json={"title": "Manual Interview", "jobTitle": "Whatever Role", "mode": "Chat"},
        headers=_headers(tenant),
    )
    iv_id = res.json()["id"]
    regenerated = await client.post(f"/interviews/{iv_id}/regenerate", headers=_headers(tenant))
    assert regenerated.status_code == 400


async def test_regenerate_single_question_replaces_only_that_one(client, tenant, captured_prompts):
    job_id = await _make_job(client, tenant)
    created = await client.post(
        "/interviews",
        json={"title": "Go Engineer Screen", "jobTitle": "Senior Go Engineer", "jobId": job_id, "mode": "Chat"},
        headers=_headers(tenant),
    )
    questions = created.json()["questions"]
    iv_id = created.json()["id"]
    target = questions[0]
    untouched_ids = [q["id"] for q in questions[1:]]

    res = await client.post(f"/interviews/{iv_id}/questions/{target['id']}/regenerate", headers=_headers(tenant))
    assert res.status_code == 200
    updated_questions = res.json()["questions"]
    assert len(updated_questions) == len(questions)

    changed = next(q for q in updated_questions if q["id"] == target["id"])
    assert changed["prompt"] == "Regenerated question about debugging."
    unchanged_ids = [q["id"] for q in updated_questions if q["id"] != target["id"]]
    assert unchanged_ids == untouched_ids
    for q in updated_questions:
        if q["id"] != target["id"]:
            assert q in questions


async def test_regenerate_unknown_question_id_is_404(client, tenant, captured_prompts):
    job_id = await _make_job(client, tenant)
    created = await client.post(
        "/interviews",
        json={"title": "Go Engineer Screen", "jobTitle": "Senior Go Engineer", "jobId": job_id, "mode": "Chat"},
        headers=_headers(tenant),
    )
    iv_id = created.json()["id"]
    res = await client.post(f"/interviews/{iv_id}/questions/not-a-real-id/regenerate", headers=_headers(tenant))
    assert res.status_code == 404


async def test_generation_is_tenant_scoped_to_the_jobs_own_tenant(client, tenant):
    """A jobId from a different tenant can't be used to generate questions."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        other = Tenant(name="Other QGen Tenant", slug=f"qgen-other-{suffix}")
        db.add(other)
        await db.commit()
        await db.refresh(other)
        db.add(User(tenant_id=other.id, email=SEED_USER_EMAIL, name="Other Recruiter", role="recruiter"))
        await db.commit()
    try:
        other_job_id = await _make_job(client, other)
        res = await client.post(
            "/interviews",
            json={"title": "Cross Tenant Attempt", "jobTitle": "x", "jobId": other_job_id, "mode": "Chat"},
            headers=_headers(tenant),
        )
        assert res.status_code == 404
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == other.id))
            await db.commit()


async def test_candidate_personalization_includes_candidate_profile_in_prompt(client, tenant, captured_prompts):
    job_id = await _make_job(client, tenant)
    # _make_candidate returns CandidateView.id, which is really an Application
    # id (see app/services/views.py::candidate_to_view) — exactly what the
    # frontend's job-candidate picker would send as `candidateId`. The router
    # resolves this down to the real Candidate row server-side.
    application_id = await _make_candidate(client, tenant, job_id)

    res = await client.post(
        "/interviews",
        json={
            "title": "Personalized Screen",
            "jobTitle": "Senior Go Engineer",
            "jobId": job_id,
            "candidateId": application_id,
            "mode": "Chat",
        },
        headers=_headers(tenant),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["candidateId"] is not None
    assert body["candidateId"] != application_id  # resolved to the Candidate's own id, not the application's
    assert len(captured_prompts) == 1
    assert "Jordan Rivera" not in captured_prompts[0]  # profile is built from structured fields, not the raw name
    assert "Acme" in captured_prompts[0] or "Kafka" in captured_prompts[0] or "Go" in captured_prompts[0]
