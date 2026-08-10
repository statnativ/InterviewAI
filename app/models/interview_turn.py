import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class InterviewTurn(Base):
    """M4: one exchange within an InterviewSession. `turn_index` is CLIENT-supplied and
    re-sent identically on retry — the `(session_id, turn_index)` unique constraint is the
    idempotency key that makes persist-before-calling safe (ADR-007). Turn 0 is the opening
    AI question from session creation — no candidate audio/transcript on that row.

    M4b: `media_type` records whether the candidate's answer was captured as audio (Voice
    mode) or video (Video mode) — `candidate_audio_path`/`candidate_audio_format` hold the
    raw uploaded media either way (the column names predate Video mode and were deliberately
    NOT renamed — an additive column is cheaper than touching every M4 call site for a
    cosmetic rename). `ai_audio_path` is always audio (TTS) regardless of `media_type` — the
    interviewer's response never becomes video; see PD-001/interview_pipeline.py, unchanged
    by M4b."""

    __tablename__ = "interview_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, complete, failed
    media_type: Mapped[str] = mapped_column(String(20), default="audio")  # audio, video
    candidate_audio_path: Mapped[str | None] = mapped_column(String(500))
    candidate_audio_format: Mapped[str | None] = mapped_column(String(20))
    transcript: Mapped[str | None] = mapped_column(Text)
    ai_text: Mapped[str | None] = mapped_column(Text)
    ai_audio_path: Mapped[str | None] = mapped_column(String(500))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_interview_turns_session_turn"),
        Index("idx_interview_turns_session", "session_id"),
        CheckConstraint(
            "status IN ('pending', 'complete', 'failed')",
            name="ck_interview_turns_status",
        ),
        CheckConstraint(
            "media_type IN ('audio', 'video')",
            name="ck_interview_turns_media_type",
        ),
    )
