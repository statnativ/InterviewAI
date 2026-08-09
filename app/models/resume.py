import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey, ARRAY, Index, func, literal_column, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50))  # pdf, docx, txt
    file_size: Mapped[int | None] = mapped_column(Integer)
    raw_text: Mapped[str | None] = mapped_column(Text)
    # Resumes don't have a fixed shape — structured extraction lives here as JSONB
    # rather than forcing every possible field into its own column.
    parsed_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_strengths: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    ai_concerns: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    years_experience: Mapped[int | None] = mapped_column(Integer)
    seniority_level: Mapped[str | None] = mapped_column(String(50))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="resumes")


# Specialized indexes defined post-class so column attributes are fully
# resolved instrumented attributes (needed for the vector/expression ones).
Index(
    "idx_resumes_embedding",
    Resume.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
Index(
    "idx_resumes_parsed_fts",
    # Built from the real column (not a bare text() string) so SQLAlchemy can
    # infer which table this expression index belongs to.
    func.to_tsvector(literal_column("'english'"), Resume.raw_text),
    postgresql_using="gin",
)
Index(
    "idx_resumes_candidate_primary",
    Resume.candidate_id,
    Resume.is_primary,
    postgresql_where=text("is_primary = TRUE"),
)
Index("idx_resumes_tenant", Resume.tenant_id)
