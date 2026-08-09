from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str
    slug: str


class TenantView(BaseModel):
    id: str
    name: str
    slug: str
    createdAt: datetime


class AdminUserCreate(BaseModel):
    tenantId: str
    email: str
    name: str | None = None
    role: str = "recruiter"  # admin, recruiter, hiring_manager
    password: str


class AdminUserView(BaseModel):
    id: str
    tenantId: str
    tenantName: str
    email: str
    name: str | None = None
    role: str
    status: str
    createdAt: datetime


class PracticeTestCreate(BaseModel):
    tenantId: str
    title: str
    mode: str = "Chat"
    questions: list[dict] = Field(default_factory=list)
    duration: int = 30


class PracticeTestView(BaseModel):
    id: str
    tenantId: str
    tenantName: str
    title: str
    mode: str
    status: str
    questions: list[dict]
    duration: int
    createdAt: datetime
