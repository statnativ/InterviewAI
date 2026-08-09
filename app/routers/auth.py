"""Real login for the admin auth module — separate from, and doesn't touch,
the M6 Phase 1/2 dev-header identity system every other router still uses.
"""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import SESSION_COOKIE_NAME, require_platform_admin
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL = timedelta(days=7)


@router.post("/login", response_model=MeResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == payload.username, User.is_platform_admin.is_(True))
    )
    user = result.scalar_one_or_none()

    # Same generic failure for "no such username" and "wrong password" — never
    # reveal which one it was.
    invalid = HTTPException(status_code=401, detail="Invalid username or password")
    if user is None or user.password_hash is None:
        raise invalid
    if not bcrypt.checkpw(payload.password.encode(), user.password_hash.encode()):
        raise invalid
    if user.status != "active":
        raise HTTPException(status_code=403, detail="This admin account is not active")

    sess = Session(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    )
    db.add(sess)
    await db.commit()

    response.set_cookie(
        SESSION_COOKIE_NAME,
        str(sess.id),
        httponly=True,
        samesite="lax",
        secure=False,  # dev only — no HTTPS locally; flip to True behind TLS in prod
        max_age=int(SESSION_TTL.total_seconds()),
    )
    return MeResponse(username=user.username, name=user.name, role="platform_admin")


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    result = await db.execute(select(Session).where(Session.user_id == user.id))
    for sess in result.scalars().all():
        await db.delete(sess)
    await db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(require_platform_admin)):
    return MeResponse(username=user.username, name=user.name, role="platform_admin")
