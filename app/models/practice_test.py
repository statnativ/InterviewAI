import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PracticeTest(Base):
    """Tenant-specific practice interview content authored by the platform
    admin (not by a tenant's own recruiters) — mirrors Interview's shape
    (mode/questions/duration) since it's the same underlying concept, just a
    different authoring path and audience (candidate prep, not a real
    screening interview)."""

    __tablename__ = "practice_tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="Chat")  # Chat, Voice, Avatar
    status: Mapped[str] = mapped_column(String(50), default="Draft")  # Draft, Active, Archived
    questions: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    duration: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("idx_practice_tests_tenant", "tenant_id"),)
