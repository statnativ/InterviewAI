from pydantic import BaseModel, Field


class TurnResultView(BaseModel):
    """Returned by session creation (turn 0, no transcript) and each
    POST /interview-sessions/{id}/turns call. `status` here is the SESSION's status after
    this turn (active/complete), not the turn row's own pending/complete/failed status —
    the caller only cares "can I send another turn."""

    sessionId: str
    turnIndex: int
    transcript: str | None = None
    aiText: str
    aiAudio: str  # base64-encoded audio bytes — see plan's file-serving-precedent rationale
    aiAudioFormat: str = "mp3"
    status: str


class TurnSummaryView(BaseModel):
    """One row in InterviewSessionView.turns — text only, no audio. Historical turns don't
    re-serve their (potentially large) audio blobs; the candidate already heard them once."""

    turnIndex: int
    status: str
    mediaType: str = "audio"  # audio, video — M4b
    transcript: str | None = None
    aiText: str | None = None


class InterviewSessionView(BaseModel):
    """Flat shape for GET /interview-sessions/{id} — reload/resume."""

    id: str
    interviewId: str
    status: str
    turns: list[TurnSummaryView] = Field(default_factory=list)
