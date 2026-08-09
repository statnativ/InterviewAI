import uuid

from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[str | None] = mapped_column(String(50))  # beginner, intermediate, advanced, expert
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1))
    source: Mapped[str | None] = mapped_column(String(50))  # parsed, self_reported, verified
