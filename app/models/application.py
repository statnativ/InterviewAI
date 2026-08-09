import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Numeric, DateTime, Text, ForeignKey, UniqueConstraint, Index, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(50), default="applied")  # applied, screening, interview, offer, hired, rejected
    stage: Mapped[str | None] = mapped_column(String(50))  # phone_screen, technical, onsite, final
    match_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    match_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    ai_screening_notes: Mapped[str | None] = mapped_column(Text)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    decision: Mapped[str] = mapped_column(String(50), default="None")  # None, Approved, Hold, Rejected
    pipeline_stage: Mapped[str] = mapped_column(String(50), default="Applied")  # Applied, Screening, Interview, Offer, Rejected
    scorecard: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    gaps: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    compare_verdict: Mapped[str] = mapped_column(String(20), default="Pass")  # Advance, Maybe, Pass
    ai_note: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id"),
        Index("idx_applications_candidate_status", "candidate_id", "status"),
        Index("idx_applications_job_status", "job_id", "status"),
    )
