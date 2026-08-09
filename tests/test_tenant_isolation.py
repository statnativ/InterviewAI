"""Cross-tenant leak tests for M6 Phase 1.

First DB-backed integration test in this repo (test_health.py/test_screening.py
are both DB-free) — runs against the real dev Postgres, same as every other
part of this project's test setup. Each test creates its own throwaway
tenants and cleans them up via cascade delete (tenant_id FKs are all
ondelete="CASCADE"), so the shared seed data (Northwind Health) is untouched.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db import async_session
from app.deps import SEED_USER_EMAIL
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

# The module-level `engine`/`async_session` in app/db.py bind their asyncpg
# connection pool to whichever event loop is running on first use. Without
# forcing every async fixture + test in this module onto the SAME loop,
# pytest-asyncio's per-test-function loop (the default) makes the second test
# reuse connections bound to a loop that's already closed -> "attached to a
# different loop" / "another operation is in progress" from asyncpg. This is
# the first DB-backed test file in the repo, so it's the first place this bites.
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def two_tenants():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        tenant_a = Tenant(name="Leak Test Co A", slug=f"leak-test-a-{suffix}")
        tenant_b = Tenant(name="Leak Test Co B", slug=f"leak-test-b-{suffix}")
        db.add_all([tenant_a, tenant_b])
        await db.commit()
        await db.refresh(tenant_a)
        await db.refresh(tenant_b)
        # get_current_user (Phase 2) needs a real user to resolve for each
        # tenant — these tests don't send X-User-Email, so it falls back to
        # SEED_USER_EMAIL, which must exist under *this* tenant too, not just
        # the real Northwind Health seed tenant.
        db.add_all(
            [
                User(tenant_id=tenant_a.id, email=SEED_USER_EMAIL, name="Leak Test Recruiter A", role="recruiter"),
                User(tenant_id=tenant_b.id, email=SEED_USER_EMAIL, name="Leak Test Recruiter B", role="recruiter"),
            ]
        )
        await db.commit()
    try:
        yield tenant_a, tenant_b
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a.id, tenant_b.id])))
            await db.commit()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _headers(tenant: Tenant) -> dict[str, str]:
    return {"X-Tenant-Id": str(tenant.id)}


async def test_jobs_are_tenant_isolated(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    created = await client.post(
        "/jobs",
        json={"title": "Tenant A Only Job", "description": "We need someone great at Go."},
        headers=_headers(tenant_a),
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    # Tenant B's list never contains tenant A's job.
    listed_b = await client.get("/jobs", headers=_headers(tenant_b))
    assert listed_b.status_code == 200
    assert all(j["id"] != job_id for j in listed_b.json())

    # Tenant B fetching it directly by id -> 404, not the record (don't leak existence).
    got_b = await client.get(f"/jobs/{job_id}", headers=_headers(tenant_b))
    assert got_b.status_code == 404

    # Tenant B can't regenerate a rubric for a job it can't see, either.
    patched_b = await client.post(f"/jobs/{job_id}/regenerate-rubric", headers=_headers(tenant_b))
    assert patched_b.status_code == 404

    # Tenant A still sees its own job fine.
    got_a = await client.get(f"/jobs/{job_id}", headers=_headers(tenant_a))
    assert got_a.status_code == 200
    assert got_a.json()["id"] == job_id


async def test_candidates_are_tenant_isolated(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    job = await client.post(
        "/jobs",
        json={"title": "Tenant A Candidate Test Job", "description": "Go and PostgreSQL required."},
        headers=_headers(tenant_a),
    )
    job_id = job.json()["id"]

    added = await client.post(
        "/candidates",
        json={
            "jobId": job_id,
            "name": "Leak Test Candidate",
            "email": "leak-test-candidate@example.com",
            "resumeText": "Experienced with Go and PostgreSQL.",
        },
        headers=_headers(tenant_a),
    )
    assert added.status_code == 201
    app_id = added.json()["candidate"]["id"]

    # Invisible in tenant B's cross-job candidate list.
    listed_b = await client.get("/candidates", headers=_headers(tenant_b))
    assert all(c["id"] != app_id for c in listed_b.json())

    # Direct fetch by application id under tenant B's header -> 404.
    got_b = await client.get(f"/candidates/{app_id}", headers=_headers(tenant_b))
    assert got_b.status_code == 404

    # Tenant B "adding a candidate" to tenant A's job id is rejected (job not
    # visible to tenant B), rather than silently attaching cross-tenant.
    cross_add = await client.post(
        "/candidates",
        json={
            "jobId": job_id,
            "name": "Should Not Be Created",
            "email": "should-not-exist@example.com",
            "resumeText": "n/a",
        },
        headers=_headers(tenant_b),
    )
    assert cross_add.status_code == 404


async def test_interviews_are_tenant_isolated(client, two_tenants):
    tenant_a, tenant_b = two_tenants

    created = await client.post(
        "/interviews",
        json={"title": "Tenant A Interview", "jobTitle": "Backend Engineer", "mode": "Chat"},
        headers=_headers(tenant_a),
    )
    assert created.status_code == 201
    iv_id = created.json()["id"]

    listed_b = await client.get("/interviews", headers=_headers(tenant_b))
    assert all(iv["id"] != iv_id for iv in listed_b.json())

    got_b = await client.get(f"/interviews/{iv_id}", headers=_headers(tenant_b))
    assert got_b.status_code == 404


async def test_same_email_allowed_across_different_tenants(client, two_tenants):
    """The whole point of the (tenant_id, email) constraint change: the same
    person's email can exist once per tenant without colliding."""
    tenant_a, tenant_b = two_tenants
    email = "shared-email@example.com"

    for tenant in (tenant_a, tenant_b):
        job = await client.post(
            "/jobs",
            json={"title": f"Job for {tenant.slug}", "description": "Any role."},
            headers=_headers(tenant),
        )
        res = await client.post(
            "/candidates",
            json={
                "jobId": job.json()["id"],
                "name": "Same Person",
                "email": email,
                "resumeText": "n/a",
            },
            headers=_headers(tenant),
        )
        assert res.status_code == 201
        assert res.json()["duplicate"] is False


async def test_unknown_tenant_id_is_404(client):
    res = await client.get("/jobs", headers={"X-Tenant-Id": str(uuid.uuid4())})
    assert res.status_code == 404


async def test_missing_tenant_header_defaults_to_seed_tenant(client):
    """No X-Tenant-Id at all -> the dev default (seed tenant), not an error —
    this is what keeps the existing frontend (which doesn't send the header
    yet, until the frontend task lands) working during the transition."""
    res = await client.get("/jobs")
    assert res.status_code == 200
    assert len(res.json()) > 0
