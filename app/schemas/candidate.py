import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    description: str
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


class CandidateCreate(BaseModel):
    """Match the frontend store's addCandidate input, plus jobId."""

    jobId: str
    name: str
    email: str
    phone: str | None = None
    source: str = "Manual Entry"
    resumeText: str = ""


class CandidatePatch(BaseModel):
    phone: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    location: str | None = None
    shortlisted: bool | None = None
    decision: str | None = None
    pipelineStage: str | None = None


class BulkPatch(BaseModel):
    candidateIds: list[str]
    action: str  # shortlist, unshortlist, decision, stage
    value: str | bool | None = None


class CandidateView(BaseModel):
    """Flat shape matching frontend/src/data/types.ts `Candidate`.

    Assembled from Application (id, jobId, score, shortlisted, decision,
    pipelineStage, scorecard, strengths, gaps, aiNote, compareVerdict,
    appliedAt) joined with the Candidate profile fields.
    """

    id: str  # application id
    jobId: str
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    source: str = "Manual Entry"
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    resumeFile: str | None = None
    yearsExp: int = 0
    currentTitle: str = "—"
    currentCompany: str = "—"
    skills: list[str] = Field(default_factory=list)
    score: int = 0
    shortlisted: bool = False
    decision: str = "None"
    pipelineStage: str = "Applied"
    summary: str = ""
    experience: list[dict] = Field(default_factory=list)
    education: str = "—"
    certifications: str = "—"
    scorecard: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    aiNote: str = ""
    compareVerdict: str = "Pass"
    appliedAt: datetime


class AddCandidateResult(BaseModel):
    candidate: CandidateView
    duplicate: bool = False


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_path: str
    file_type: str | None
    file_size: int | None
    parsed_data: dict
    is_primary: bool
    created_at: datetime
