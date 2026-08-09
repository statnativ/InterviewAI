"""Master-admin panel: create tenants, create/approve tenant users, author
tenant-specific Practice Tests. Every route requires a real platform-admin
session (require_platform_admin) — this is a cross-tenant surface, so it
deliberately does NOT use get_current_tenant/require_roles (those assume a
single acting tenant, which doesn't apply here).
"""
import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_platform_admin
from app.models.practice_test import PracticeTest
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserView,
    PracticeTestCreate,
    PracticeTestView,
    TenantCreate,
    TenantView,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])


def _tenant_view(t: Tenant) -> TenantView:
    return TenantView(id=str(t.id), name=t.name, slug=t.slug, createdAt=t.created_at)


def _user_view(u: User, tenant_name: str) -> AdminUserView:
    return AdminUserView(
        id=str(u.id),
        tenantId=str(u.tenant_id),
        tenantName=tenant_name,
        email=u.email,
        name=u.name,
        role=u.role,
        status=u.status,
        createdAt=u.created_at,
    )


def _practice_test_view(p: PracticeTest, tenant_name: str) -> PracticeTestView:
    return PracticeTestView(
        id=str(p.id),
        tenantId=str(p.tenant_id),
        tenantName=tenant_name,
        title=p.title,
        mode=p.mode,
        status=p.status,
        questions=p.questions,
        duration=p.duration,
        createdAt=p.created_at,
    )


# ---- Tenants ----

@router.get("/tenants", response_model=list[TenantView])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return [_tenant_view(t) for t in result.scalars().all()]


@router.post("/tenants", response_model=TenantView, status_code=201)
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Tenant).where(Tenant.slug == payload.slug))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A tenant with this slug already exists")
    tenant = Tenant(name=payload.name, slug=payload.slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return _tenant_view(tenant)


# ---- Users (create -> pending -> approve) ----

@router.get("/users", response_model=list[AdminUserView])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User, Tenant.name)
        .join(Tenant, User.tenant_id == Tenant.id)
        .order_by(User.created_at.desc())
    )
    return [_user_view(u, tenant_name) for u, tenant_name in result.all()]


@router.post("/users", response_model=AdminUserView, status_code=201)
async def create_user(payload: AdminUserCreate, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(payload.tenantId))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    email_key = payload.email.strip().lower()
    existing = (
        await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == email_key))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists in this tenant")

    user = User(
        tenant_id=tenant.id,
        email=email_key,
        name=payload.name,
        role=payload.role,
        password_hash=bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode(),
        status="pending",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_view(user, tenant.name)


@router.post("/users/{user_id}/approve", response_model=AdminUserView)
async def approve_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None or user.is_platform_admin:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "active"
    await db.commit()
    await db.refresh(user)
    tenant = await db.get(Tenant, user.tenant_id)
    return _user_view(user, tenant.name if tenant else "")


@router.post("/users/{user_id}/disable", response_model=AdminUserView)
async def disable_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None or user.is_platform_admin:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "disabled"
    await db.commit()
    await db.refresh(user)
    tenant = await db.get(Tenant, user.tenant_id)
    return _user_view(user, tenant.name if tenant else "")


# ---- Practice Tests (tenant-specific) ----

@router.get("/practice-tests", response_model=list[PracticeTestView])
async def list_practice_tests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PracticeTest, Tenant.name)
        .join(Tenant, PracticeTest.tenant_id == Tenant.id)
        .order_by(PracticeTest.created_at.desc())
    )
    return [_practice_test_view(p, tenant_name) for p, tenant_name in result.all()]


@router.post("/practice-tests", response_model=PracticeTestView, status_code=201)
async def create_practice_test(payload: PracticeTestCreate, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(payload.tenantId))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    practice_test = PracticeTest(
        tenant_id=tenant.id,
        title=payload.title,
        mode=payload.mode,
        questions=payload.questions,
        duration=payload.duration,
        status="Active",
    )
    db.add(practice_test)
    await db.commit()
    await db.refresh(practice_test)
    return _practice_test_view(practice_test, tenant.name)
