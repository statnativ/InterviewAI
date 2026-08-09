"""Admin auth module tests: login, session cookie, and that this auth system
is fully isolated from the M6 Phase 1/2 dev-header system every other route
still uses. Same conventions as test_tenant_isolation.py/test_rbac.py — real
dev DB, explicit cleanup, session-scoped event loop.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db import async_session
from app.main import app
from app.models.tenant import Tenant
from app.seed import PLATFORM_ADMIN_PASSWORD, PLATFORM_ADMIN_USERNAME

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def logged_in_admin(client):
    res = await client.post(
        "/auth/login", json={"username": PLATFORM_ADMIN_USERNAME, "password": PLATFORM_ADMIN_PASSWORD}
    )
    assert res.status_code == 200
    yield client
    await client.post("/auth/logout")


@pytest_asyncio.fixture
async def scratch_tenant():
    suffix = uuid.uuid4().hex[:8]
    async with async_session() as db:
        tenant = Tenant(name="Admin Test Co", slug=f"admin-test-{suffix}")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
    try:
        yield tenant
    finally:
        async with async_session() as db:
            await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()


async def test_login_wrong_password_is_401(client):
    res = await client.post("/auth/login", json={"username": PLATFORM_ADMIN_USERNAME, "password": "wrong"})
    assert res.status_code == 401


async def test_login_unknown_username_is_401(client):
    res = await client.post("/auth/login", json={"username": "nobody", "password": "irrelevant"})
    assert res.status_code == 401


async def test_login_correct_credentials_succeeds(client):
    res = await client.post(
        "/auth/login", json={"username": PLATFORM_ADMIN_USERNAME, "password": PLATFORM_ADMIN_PASSWORD}
    )
    assert res.status_code == 200
    assert res.json()["username"] == PLATFORM_ADMIN_USERNAME
    assert "session_id" in res.cookies
    await client.post("/auth/logout")


async def test_admin_routes_require_session(client):
    res = await client.get("/admin/tenants")
    assert res.status_code == 401


async def test_regular_tenant_header_does_not_grant_admin_access(client):
    """The two auth systems must stay isolated: a valid X-Tenant-Id/X-User-Email
    combo (M6 Phase 1/2) is not a substitute for a real admin session."""
    res = await client.get(
        "/admin/tenants",
        headers={
            "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Email": "riley@northwindhealth.com",
        },
    )
    assert res.status_code == 401


async def test_logout_invalidates_the_session(client):
    await client.post("/auth/login", json={"username": PLATFORM_ADMIN_USERNAME, "password": PLATFORM_ADMIN_PASSWORD})
    assert (await client.get("/admin/tenants")).status_code == 200
    await client.post("/auth/logout")
    assert (await client.get("/admin/tenants")).status_code == 401


async def test_create_tenant(logged_in_admin):
    slug = f"new-co-{uuid.uuid4().hex[:8]}"
    res = await logged_in_admin.post("/admin/tenants", json={"name": "New Co", "slug": slug})
    assert res.status_code == 201
    body = res.json()
    assert body["slug"] == slug

    # cleanup
    async with async_session() as db:
        await db.execute(delete(Tenant).where(Tenant.slug == slug))
        await db.commit()


async def test_create_approve_disable_user_lifecycle(logged_in_admin, scratch_tenant):
    email = f"pending-{uuid.uuid4().hex[:8]}@example.com"
    created = await logged_in_admin.post(
        "/admin/users",
        json={
            "tenantId": str(scratch_tenant.id),
            "email": email,
            "name": "Pending Person",
            "role": "recruiter",
            "password": "TempPass123!",
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert user["status"] == "pending"
    assert user["tenantName"] == scratch_tenant.name

    listed = await logged_in_admin.get("/admin/users")
    assert any(u["id"] == user["id"] and u["status"] == "pending" for u in listed.json())

    approved = await logged_in_admin.post(f"/admin/users/{user['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"

    disabled = await logged_in_admin.post(f"/admin/users/{user['id']}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"


async def test_create_practice_test_is_tenant_scoped(logged_in_admin, scratch_tenant):
    res = await logged_in_admin.post(
        "/admin/practice-tests",
        json={
            "tenantId": str(scratch_tenant.id),
            "title": "System Design Practice",
            "mode": "Chat",
            "duration": 30,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["tenantId"] == str(scratch_tenant.id)
    assert body["tenantName"] == scratch_tenant.name

    listed = await logged_in_admin.get("/admin/practice-tests")
    assert any(p["id"] == body["id"] for p in listed.json())
