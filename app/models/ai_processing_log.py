import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AIProcessingLog(Base):
    __tablename__ = "ai_processing_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str | None] = mapped_column(String(50))  # resume, job, application
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation: Mapped[str | None] = mapped_column(String(100))  # parse, embed, screen, summarize, match
    model_used: Mapped[str | None] = mapped_column(String(100))  # gpt-4, text-embedding-ada-002
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    status: Mapped[str | None] = mapped_column(String(50))  # success, failed, partial
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
