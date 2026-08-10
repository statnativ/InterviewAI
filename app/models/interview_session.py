import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class InterviewSession(Base):
    """M4: one candidate's attempt at a Voice-mode interview. `id` is itself the bearer
    credential for every turn request — deliberately, since no candidate identity/auth
    system exists anywhere in this codebase (see ADR-008). `candidate_id` is nullable: a
    `shared` interview link has no candidate to attribute the session to.

    M5: `evaluation_status`/`score`/`scorecard`/`strengths`/`gaps`/`ai_verdict`/`ai_note`/
    `evaluation_error`/`evaluated_at` are the AI's own output — populated by
    `app/services/interview_evaluator.py`, running inside a Celery task, once the whole
    transcript is scored against the linked job's rubric (mirrors `Application`'s scorecard
    shape exactly, fed a transcript instead of a résumé profile). `decision` is the separate,
    human-set override (`None`/`Approved`/`Hold`/`Rejected`, mirrors `Application.decision`) —
    a recruiter can set it any time, and it never touches the AI-owned fields above, same
    separation `Application.decision` already keeps from its own scorecard."""

    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, complete, abandoned
    # idle, pending, complete, failed — a 4-state design, richer than applications.judge_status's
    # 3-state one: there's no score_method-equivalent field here to infer "done" from absence.
    evaluation_status: Mapped[str] = mapped_column(String(20), default="idle")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scorecard: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    gaps: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    ai_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Advance, Maybe, Pass
    ai_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision: Mapped[str] = mapped_column(String(50), default="None")  # None, Approved, Hold, Rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_interview_sessions_tenant", "tenant_id"),
        Index("idx_interview_sessions_interview", "interview_id"),
        CheckConstraint(
            "status IN ('active', 'complete', 'abandoned')",
            name="ck_interview_sessions_status",
        ),
        CheckConstraint(
            "evaluation_status IN ('idle', 'pending', 'complete', 'failed')",
            name="ck_interview_sessions_evaluation_status",
        ),
    )
