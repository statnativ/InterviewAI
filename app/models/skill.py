import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, DateTime, ARRAY, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(100))  # programming, framework, tool, soft_skill, domain
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# Defined post-class (not in __table_args__) so `Skill.embedding` is a fully
# resolved instrumented attribute rather than a mid-construction MappedColumn.
Index(
    "idx_skills_embedding",
    Skill.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
