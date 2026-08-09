import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable only for platform admins (see the CHECK constraint below) — every regular,
    # tenant-scoped user still must have one.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="recruiter")  # admin, recruiter, hiring_manager
    # Real-auth columns (admin auth module) — nullable because most rows created via the old
    # dev-header flow (M6 Phase 1/2) still have neither.
    username: Mapped[str | None] = mapped_column(String(100))  # only platform admins log in by username
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")  # pending, active, disabled
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("idx_users_tenant", "tenant_id"),
        Index("uq_users_username", "username", unique=True, postgresql_where=text("username IS NOT NULL")),
        CheckConstraint(
            "(tenant_id IS NULL AND is_platform_admin) OR (tenant_id IS NOT NULL AND NOT is_platform_admin)",
            name="ck_users_platform_admin_no_tenant",
        ),
    )
