import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(50), default="Chat")  # Chat, Voice, Avatar
    status: Mapped[str] = mapped_column(String(50), default="Draft")  # Draft, Active, Archived
    questions: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    duration: Mapped[int] = mapped_column(Integer, default=30)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_interviews_tenant", "tenant_id"),
        Index("idx_interviews_job", "job_id"),
        Index("idx_interviews_candidate", "candidate_id"),
        CheckConstraint(
            "NOT (shared AND candidate_id IS NOT NULL)",
            name="ck_interviews_no_shared_personalized",
        ),
    )
