"""M5: recruiter-facing view shapes for interview evaluation/review — see
app/routers/interview_reports.py. Deliberately separate from
app/schemas/interview_session.py, which is the candidate-facing (no
tenant/role auth) surface's own DTOs."""
from datetime import datetime

from pydantic import BaseModel, Field


class InterviewSessionSummaryView(BaseModel):
    """One row in GET /interviews/{interview_id}/sessions."""

    id: str
    candidateId: str | None = None
    candidateName: str | None = None
    status: str
    evaluationStatus: str
    score: int | None = None
    decision: str
    completedAt: datetime | None = None


class ReportTurnView(BaseModel):
    turnIndex: int
    status: str
    mediaType: str
    transcript: str | None = None
    aiText: str | None = None


class InterviewReportView(BaseModel):
    """Full shape for GET /interview-sessions/{session_id}/report."""

    id: str
    interviewId: str
    candidateId: str | None = None
    candidateName: str | None = None
    status: str
    turns: list[ReportTurnView] = Field(default_factory=list)
    evaluationStatus: str
    score: int | None = None
    scorecard: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    aiVerdict: str | None = None
    aiNote: str | None = None
    evaluationError: str | None = None
    decision: str
    completedAt: datetime | None = None


class DecisionPatch(BaseModel):
    decision: str
