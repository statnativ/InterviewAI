"""RBAC enforcement matrix tests for M6 Phase 2 (app/services/authz.py).

Table-driven per the Identity & Access plan: every route class x every role
-> the expected status code. One throwaway tenant with one user per role,
cleaned up via cascade delete on the tenant (matches test_tenant_isolation.py's
convention — this repo's tests run against the real dev DB, no test-DB
isolation layer exists yet).
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db import async_session
from app.main import app
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.tenant import Tenant
from app.models.user import User
from app.services.authz import ADMIN, HIRING_MANAGER, RECRUITER

pytestmark = pytest.mark.asyncio(loop_scope="session")

ALL = (ADMIN, RECRUITER, HIRING_MANAGER)
ROLE_EMAILS = {
    ADMIN: "admin@rbac-test.example.com",
    RECRUITER: "recruiter@rbac-test.example.com",
    HIRING_MANAGER: "hm@rbac-test.example.com",
}


@pytest_asyncio.fixture
async def rbac_fixture():
    """One tenant, one user per role, one job/candidate/interview to act on."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        tenant = Tenant(name="RBAC Test Co", slug=f"rbac-test-{suffix}")
        db.add(tenant)
        await db.flush()

        db.add_all(
            User(tenant_id=tenant.id, email=email, role=role) for role, email in ROLE_EMAILS.items()
        )

        job = Job(tenant_id=tenant.id, title="RBAC Test Job", description="Go and PostgreSQL required.")
        db.add(job)
        await db.flush()

        candidate = Candidate(tenant_id=tenant.id, name="RBAC Candidate", email=f"rbac-cand-{suffix}@example.com")
        db.add(candidate)
        await db.flush()

        application = Application(tenant_id=tenant.id, candidate_id=candidate.id, job_id=job.id)
        db.add(application)

        interview = Interview(tenant_id=tenant.id, title="RBAC Test Interview", job_title="RBAC Test Job")
        db.add(interview)

        await db.commit()
        await db.refresh(job)
        await db.refresh(application)
        await db.refresh(interview)

    try:
        yield tenant, job, application, interview
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _headers(tenant: Tenant, role: str) -> dict[str, str]:
    return {"X-Tenant-Id": str(tenant.id), "X-User-Email": ROLE_EMAILS[role]}


@pytest.mark.parametrize("role", ALL)
async def test_read_routes_open_to_every_role(client, rbac_fixture, role):
    tenant, job, application, interview = rbac_fixture
    headers = _headers(tenant, role)

    assert (await client.get("/jobs", headers=headers)).status_code == 200
    assert (await client.get(f"/jobs/{job.id}", headers=headers)).status_code == 200
    assert (await client.get(f"/jobs/{job.id}/candidates", headers=headers)).status_code == 200
    assert (await client.get("/candidates", headers=headers)).status_code == 200
    assert (await client.get(f"/candidates/{application.id}", headers=headers)).status_code == 200
    assert (await client.get("/interviews", headers=headers)).status_code == 200
    assert (await client.get(f"/interviews/{interview.id}", headers=headers)).status_code == 200


@pytest.mark.parametrize("role,expected", [(ADMIN, 200), (RECRUITER, 200), (HIRING_MANAGER, 403)])
async def test_job_writes_are_recruiter_and_admin_only(client, rbac_fixture, role, expected):
    tenant, job, _application, _interview = rbac_fixture
    headers = _headers(tenant, role)

    res = await client.patch(f"/jobs/{job.id}", json={"title": "Updated by RBAC test"}, headers=headers)
    assert res.status_code == expected

    res = await client.post(f"/jobs/{job.id}/regenerate-rubric", headers=headers)
    assert res.status_code == expected

    res = await client.post(f"/jobs/{job.id}/save-version", headers=headers)
    assert res.status_code == expected


@pytest.mark.parametrize("role,expected", [(ADMIN, 201), (RECRUITER, 201), (HIRING_MANAGER, 403)])
async def test_job_create_is_recruiter_and_admin_only(client, rbac_fixture, role, expected):
    tenant, *_ = rbac_fixture
    res = await client.post(
        "/jobs",
        json={"title": f"New job by {role}", "description": "Some JD text."},
        headers=_headers(tenant, role),
    )
    assert res.status_code == expected


@pytest.mark.parametrize("role,expected", [(ADMIN, 201), (RECRUITER, 201), (HIRING_MANAGER, 403)])
async def test_candidate_create_is_recruiter_and_admin_only(client, rbac_fixture, role, expected):
    tenant, job, _application, _interview = rbac_fixture
    res = await client.post(
        "/candidates",
        json={
            "jobId": str(job.id),
            "name": f"Candidate added by {role}",
            "email": f"new-{role}@example.com",
            "resumeText": "n/a",
        },
        headers=_headers(tenant, role),
    )
    assert res.status_code == expected


@pytest.mark.parametrize("role,expected", [(ADMIN, 200), (RECRUITER, 200), (HIRING_MANAGER, 403)])
async def test_candidate_writes_are_recruiter_and_admin_only(client, rbac_fixture, role, expected):
    tenant, _job, application, _interview = rbac_fixture
    headers = _headers(tenant, role)

    res = await client.patch(f"/candidates/{application.id}", json={"notes": "touched by RBAC test"}, headers=headers)
    assert res.status_code == expected

    res = await client.post(f"/candidates/{application.id}/screen", headers=headers)
    assert res.status_code == expected

    res = await client.post(
        "/candidates/bulk",
        json={"candidateIds": [str(application.id)], "action": "shortlist"},
        headers=headers,
    )
    assert res.status_code == (200 if expected == 200 else expected)


@pytest.mark.parametrize("role", ALL)
async def test_interview_writes_open_to_every_role(client, rbac_fixture, role):
    tenant, _job, _application, interview = rbac_fixture
    headers = _headers(tenant, role)

    res = await client.patch(f"/interviews/{interview.id}", json={"title": "Updated by RBAC test"}, headers=headers)
    assert res.status_code == 200

    res = await client.post(
        "/interviews",
        json={"title": f"New interview by {role}", "jobTitle": "RBAC Test Job", "mode": "Chat"},
        headers=headers,
    )
    assert res.status_code == 201


async def test_unrecognized_user_email_is_401(client, rbac_fixture):
    tenant, *_ = rbac_fixture
    res = await client.get(
        "/jobs", headers={"X-Tenant-Id": str(tenant.id), "X-User-Email": "nobody@example.com"}
    )
    assert res.status_code == 401
