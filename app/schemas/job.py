from datetime import datetime

from pydantic import BaseModel, Field


class JobView(BaseModel):
    """Flat shape matching frontend/src/data/types.ts `Job`."""

    id: str
    title: str
    department: str | None = None
    location: str | None = None
    type: str | None = None  # employment_type
    status: str = "Open"
    description: str = ""
    rubric: list[dict] = Field(default_factory=list)
    versions: list[dict] = Field(default_factory=list)
    createdAt: datetime


class JobCreate(BaseModel):
    title: str
    description: str = ""
    department: str | None = None
    location: str | None = None
    type: str | None = None
    status: str = "Draft"


class JobPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    department: str | None = None
    location: str | None = None
    type: str | None = None
    status: str | None = None
