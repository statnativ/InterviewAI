import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewView(BaseModel):
    """Flat shape matching frontend/src/data/types.ts `Interview`."""

    id: str
    title: str
    jobTitle: str
    mode: str = "Chat"
    status: str = "Draft"
    questions: list[dict] = Field(default_factory=list)
    duration: int = 30
    createdAt: datetime
    shared: bool = False


class InterviewCreate(BaseModel):
    title: str
    jobTitle: str
    mode: str = "Chat"
    questions: list[dict] = Field(default_factory=list)
    duration: int = 30


class InterviewPatch(BaseModel):
    title: str | None = None
    jobTitle: str | None = None
    mode: str | None = None
    status: str | None = None
    questions: list[dict] | None = None
    duration: int | None = None
    shared: bool | None = None


class QuestionCreate(BaseModel):
    prompt: str
    type: str = "Behavioral"
    difficulty: str = "Medium"
