"""Request-scoped identity dependencies: "which tenant" and (Phase 2) "which
user" is making this request. Both are dev-mode stand-ins today — headers
instead of a real session — and both get replaced by Phase 3's real
session-backed auth behind the same dependency signature, so no route handler
changes when SSO lands.
"""
import uuid
from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.interview_session import InterviewSession
from app.models.session import Session
from app.models.tenant import Tenant
from app.models.user import User

SESSION_COOKIE_NAME = "session_id"

# The one seed tenant (Northwind Health) — must match migration
# c3d4e5f6a7b8's SEED_TENANT_ID and app/seed.py's tenant row.
SEED_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


async def get_current_tenant(
    x_tenant_id: uuid.UUID | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve the acting tenant from the X-Tenant-Id header, defaulting to
    the seed tenant in dev. 404s (not a bare 400) on an unknown id — an
    unrecognized tenant should look the same as "nothing here" from the
    caller's side, not reveal that the id format was merely well-formed."""
    tenant_id = x_tenant_id or SEED_TENANT_ID
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Unknown tenant")
    return tenant


# The one seed user (Riley Hoffman, recruiter) — the dev default identity
# when no X-User-Email header is sent, matching app/seed.py.
SEED_USER_EMAIL = "riley@northwindhealth.com"


async def get_current_user(
    x_user_email: str | None = Header(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the acting user from the X-User-Email header (scoped to the
    already-resolved tenant), defaulting to the seed recruiter in dev. A
    401 here means "no identity could be established" — distinct from
    require_roles' 403 ("identity established, wrong role")."""
    email = (x_user_email or SEED_USER_EMAIL).strip().lower()
    result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def require_roles(*roles: str):
    """Dependency factory: Depends(require_roles("admin", "recruiter")).
    401 if no user could be resolved at all (see get_current_user); 403 if
    the resolved user's role isn't in the allowed set."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _check


async def require_platform_admin(
    session_id: uuid.UUID | None = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The admin auth module's real (session-cookie-based) identity check —
    fully separate from get_current_tenant/get_current_user/require_roles
    above, which stay exactly as Phase 1/2 left them (client-supplied
    headers). A platform admin isn't a tenant user at all (tenant_id is NULL,
    enforced by the DB CHECK constraint), so it doesn't fit that model.
    401 for any failure mode (no cookie, unknown/expired session, or a real
    session for a non-admin user) — deliberately not distinguishing these to
    a caller, same "don't leak why" reasoning as get_current_tenant."""
    if session_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sess = await db.get(Session, session_id)
    if sess is None or sess.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    user = await db.get(User, sess.user_id)
    if user is None or not user.is_platform_admin or user.status != "active":
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_current_interview_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InterviewSession:
    """M4: the candidate-facing counterpart to get_current_tenant/require_roles above —
    genuinely different, not an oversight. There is no candidate identity anywhere in this
    codebase (no login, no header to trust from an anonymous candidate), so
    `interview_sessions.id` itself is the bearer credential (see ADR-008). Deliberately does
    NOT call get_current_tenant: tenant scoping for a session is derived transitively
    (interview_id -> Interview.tenant_id) at session-creation time and stored directly on the
    row, not asserted per-request via a header nobody sends here.

    404s only on a genuinely unknown session id — this dependency does not judge whether the
    session's current status (active/complete/abandoned) is valid for the calling route; each
    route decides that for itself (e.g. POSTing a turn to a completed session is a 409, not a
    404 — those are different failure meanings this codebase is otherwise careful to keep
    separate, see interviews.py's 409 on ck_interviews_no_shared_personalized)."""
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session
