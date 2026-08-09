from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  — registers every table on Base.metadata before any request
from app.routers import candidates, health, interviews, jobs

app = FastAPI(title="AI Interview Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(interviews.router)
