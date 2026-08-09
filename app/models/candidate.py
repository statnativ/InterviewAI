import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Integer, Boolean, ARRAY, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(255))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(100), default="Manual Entry")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    resume_file: Mapped[str | None] = mapped_column(String(255))
    years_exp: Mapped[int] = mapped_column(Integer, default=0)
    current_title: Mapped[str] = mapped_column(String(255), default="—")
    current_company: Mapped[str] = mapped_column(String(255), default="—")
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    education: Mapped[str] = mapped_column(Text, default="—")
    certifications: Mapped[str] = mapped_column(Text, default="—")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    resumes: Mapped[list["Resume"]] = relationship(back_populates="candidate", order_by="Resume.created_at.desc()")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_candidates_tenant_email"),
        Index("idx_candidates_tenant", "tenant_id"),
    )
