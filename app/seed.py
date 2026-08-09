"""Seed the database from the generated frontend seed.

Idempotent: skips jobs/candidates/interviews that already exist (matched by
original synthetic id via an "original_id" side-table? no — matched by title/email).

Writes the canonical seed (37 jobs, 228 candidate applications, 2 interviews)
into Postgres so the API serves the same data the frontend used to hold in
localStorage.

Usage: venv/bin/python -m app.seed
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import select

from app.db import async_session
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

SEED_TS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "generated-seed.ts"

SEED_INTERVIEWS = [
    {
        "title": "Senior Backend Engineer — Technical Screen",
        "jobTitle": "Senior Backend Engineer",
        "mode": "Chat",
        "status": "Active",
        "duration": 45,
        "shared": True,
        "questions": [
            {"id": "q1", "prompt": "Walk me through how you'd design a rate limiter for a public API.", "type": "System Design", "difficulty": "Medium"},
            {"id": "q2", "prompt": "Describe a production incident you led the response for. What was the root cause?", "type": "Behavioral", "difficulty": "Medium"},
            {"id": "q3", "prompt": "How would you shard a PostgreSQL database that's outgrown a single instance?", "type": "Technical", "difficulty": "Hard"},
            {"id": "q4", "prompt": "Tell me about a time you disagreed with a technical decision on your team.", "type": "Culture", "difficulty": "Easy"},
        ],
    },
    {
        "title": "Product Designer — Portfolio Walkthrough",
        "jobTitle": "Product Designer",
        "mode": "Voice",
        "status": "Active",
        "duration": 30,
        "shared": False,
        "questions": [
            {"id": "q1", "prompt": "Walk me through a project where the initial design didn't work and how you iterated.", "type": "Behavioral", "difficulty": "Medium"},
            {"id": "q2", "prompt": "How do you decide when a design is ready to ship vs. needs more research?", "type": "Culture", "difficulty": "Easy"},
        ],
    },
    {
        "title": "Staff SRE — Incident Leadership",
        "jobTitle": "Staff SRE",
        "mode": "Avatar",
        "status": "Archived",
        "duration": 40,
        "shared": True,
        "questions": [
            {"id": "q1", "prompt": "Walk me through the largest outage you've led the response for.", "type": "System Design", "difficulty": "Hard"},
            {"id": "q2", "prompt": "How do you balance on-call load across a team of 6?", "type": "Behavioral", "difficulty": "Medium"},
        ],
    },
]


def _parse_ts_array(src: str, name: str) -> list[dict]:
    m = re.search(rf"export const {name}:\s*\w+\[\]\s*=\s*(\[.*?\])\s*;", src, re.S)
    if not m:
        raise RuntimeError(f"could not find export const {name} in {src[:200]}")
    body = m.group(1)
    # The TS literal is valid JSON apart from trailing commas inside objects,
    # which json.loads rejects. Strip trailing commas before object/array close.
    cleaned = re.sub(r",\s*([}\]])", r"\1", body)
    return json.loads(cleaned)


def _load_ts(path: Path) -> tuple[list[dict], list[dict]]:
    src = path.read_text()
    jobs = _parse_ts_array(src, "jobs") if "jobs" in src else []
    candidates = _parse_ts_array(src, "candidates") if "candidates" in src else []
    return jobs, candidates


async def seed() -> None:
    jobs, candidates = _load_ts(SEED_TS)
    interviews = SEED_INTERVIEWS

    async with async_session() as db:
        org = await db.execute(select(User).where(User.email == "riley@northwindhealth.com"))
        org_user = org.scalar_one_or_none()

        seen_emails: dict[str, Candidate] = {}

        for j in jobs:
            existing = (await db.execute(select(Job).where(Job.title == j["title"]))).scalars().first()
            if existing:
                continue
            db.add(
                Job(
                    title=j["title"],
                    department=j.get("department"),
                    location=j.get("location"),
                    employment_type=j.get("type"),
                    status=j.get("status", "Open"),
                    description=j.get("description", ""),
                    rubric=j.get("rubric", []),
                    versions=j.get("versions", []),
                    posted_by=org_user.id if org_user else None,
                )
            )
        await db.commit()
        print(f"Jobs seeded: {len(jobs)}")

        # Resolve the synthetic jobId (a slug) -> Job via the seed title index.
        title_by_id = {j["id"]: j["title"] for j in jobs}
        created = 0
        for c in candidates:
            title = title_by_id.get(c["jobId"])
            if title is None:
                continue
            job = (await db.execute(select(Job).where(Job.title == title))).scalars().first()
            if job is None:
                continue
            person = seen_emails.get(c["email"])
            if person is None:
                person = Candidate(
                    name=c["name"],
                    email=c["email"],
                    phone=c.get("phone"),
                    location=c.get("location"),
                    source=c.get("source", "Manual Entry"),
                    tags=c.get("tags", []),
                    notes=c.get("notes", ""),
                    resume_file=c.get("resumeFile"),
                    years_exp=c.get("yearsExp", 0),
                    current_title=c.get("currentTitle", "—"),
                    current_company=c.get("currentCompany", "—"),
                    skills=c.get("skills", []),
                    summary=c.get("summary", ""),
                    experience=c.get("experience", []),
                    education=c.get("education", "—"),
                    certifications=c.get("certifications", "—"),
                )
                db.add(person)
                await db.flush()
                seen_emails[c["email"]] = person

            dup = (
                await db.execute(
                    select(Application).where(
                        Application.candidate_id == person.id,
                        Application.job_id == job.id,
                    )
                )
            ).scalars().first()
            if dup:
                continue
            db.add(
                Application(
                    candidate_id=person.id,
                    job_id=job.id,
                    status="screening",
                    match_score=c.get("score", 0),
                    shortlisted=c.get("shortlisted", False),
                    decision=c.get("decision", "None"),
                    pipeline_stage=c.get("pipelineStage", "Applied"),
                    scorecard=c.get("scorecard", []),
                    strengths=c.get("strengths", []),
                    gaps=c.get("gaps", []),
                    compare_verdict=c.get("compareVerdict", "Pass"),
                    ai_note=c.get("aiNote", ""),
                    applied_at=_iso(c.get("appliedAt")),
                )
            )
            created += 1
        await db.commit()
        print(f"Candidates seeded: {created} applications across {len(seen_emails)} people")

        for iv in interviews:
            existing = (
                await db.execute(select(Interview).where(Interview.title == iv["title"]))
            ).scalars().first()
            if existing:
                continue
            db.add(
                Interview(
                    title=iv["title"],
                    job_title=iv.get("jobTitle", ""),
                    mode=iv.get("mode", "Chat"),
                    status=iv.get("status", "Draft"),
                    questions=iv.get("questions", []),
                    duration=iv.get("duration", 30),
                    shared=iv.get("shared", False),
                )
            )
        await db.commit()
        print(f"Interviews seeded: {len(interviews)}")


def _iso(value: str | None):
    from datetime import datetime

    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


if __name__ == "__main__":
    asyncio.run(seed())
