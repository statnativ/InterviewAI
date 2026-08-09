"""Convert canonical synthetic data into the frontend seed shape.

DERIVED state (never authored in the data) is computed here, deterministically:

    * Job.rubric            <- requiredSkills (level -> tag, weight passthrough)
    * Candidate.score       <- must-have skill coverage against the job's rubric
    * Candidate.scorecard   <- per-criterion derived score + evidence note
    * Candidate.pipelineStage <- application.status
    * Candidate.compareVerdict <- score bands

Scoring formula (documented so it can be argued with):
    match_ratio = matched_musthave_weight / total_musthave_weight
    nice_bonus  = 5 * (matched_nice_weight / total_nice_weight)
    score       = round(30 + 65 * match_ratio + nice_bonus), capped at 99

So a candidate covering every must-have lands ~95-99; missing a core must-have drops into
the 60s-70s; missing most must-haves lands ~30-50. The band is intentionally wide so the
deliberately weak candidates in the pools read as weak in the ATS ranking.

Usage: python scripts/synthetic/convert/to_frontend_seed.py
Writes: data/synthetic/out/frontend-seed.ts
        frontend/src/data/generated-seed.ts (what the app actually consumes)
"""

from __future__ import annotations

import json
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "data" / "synthetic"
JOBS_DIR = ROOT / "jobs"
PEOPLE_DIR = ROOT / "people"
APPS_DIR = ROOT / "applications"
OUT = ROOT / "out" / "frontend-seed.ts"
FRONTEND_OUT = ROOT.parent.parent / "frontend" / "src" / "data" / "generated-seed.ts"

TAG_BY_LEVEL = {"must-have": "Must-have", "nice-to-have": "Nice-to-have", "disqualifying": "Disqualifying"}
STAGE_BY_STATUS = {"Applied": "Applied", "Screening": "Screening", "Interview": "Interview", "Offer": "Offer", "Rejected": "Rejected"}
VERDICT_BY_SCORE = lambda s: "Advance" if s >= 80 else "Maybe" if s >= 55 else "Pass"

SOURCES = ["LinkedIn", "Employee Referral", "Company Careers Page", "Job Board", "Hacker News", "University Recruiting"]
DOMAIN_TAG = {
    "backend": "Backend",
    "frontend": "Frontend",
    "data": "Data",
    "mobile": "Mobile",
    "infra": "Infrastructure",
    "security": "Security",
    "qa": "Quality",
    "architecture": "Architecture",
    "ai": "AI / ML",
}


def derive_source(person: dict) -> str:
    return SOURCES[zlib.crc32(person["id"].encode()) % len(SOURCES)]


def derive_tags(person: dict) -> list[str]:
    seniority = (
        "Senior" if person["yearsExp"] >= 8 else "Mid-level" if person["yearsExp"] >= 4 else "Junior"
    )
    tags = [seniority, DOMAIN_TAG.get(person["primaryDomain"], person["primaryDomain"])]
    if "remote" in person.get("location", "").lower():
        tags.append("Remote")
    return tags


def load_many(directory: Path) -> dict[str, dict]:
    return {d["id"]: d for d in (json.loads(p.read_text()) for p in sorted(directory.glob("*.json")))}


def period(from_ym: str, to_ym: str | None) -> str:
    end = "Present" if to_ym is None else to_ym
    return f"{from_ym} — {end}"


def derive_score(job: dict, person: dict) -> tuple[int, list[dict]]:
    skills = set(person["skills"])
    weights = {s["name"]: s["weight"] for s in job["requiredSkills"]}
    must = {s["name"]: s for s in job["requiredSkills"] if s["level"] == "must-have"}
    nice = {s["name"]: s for s in job["requiredSkills"] if s["level"] == "nice-to-have"}
    total_must = sum(s["weight"] for s in must.values()) or 1
    total_nice = sum(s["weight"] for s in nice.values()) or 1
    matched_must = sum(w for name, w in weights.items() if name in must and name in skills)
    matched_nice = sum(w for name, w in weights.items() if name in nice and name in skills)
    score = min(99, round(30 + 65 * (matched_must / total_must) + 5 * (matched_nice / total_nice)))

    scorecard = []
    for s in sorted(job["requiredSkills"], key=lambda x: -x["weight"]):
        name = s["name"]
        hit = name in skills
        sub = 100 if hit else 35
        note = (
            f"Direct evidence of {name} on resume."
            if hit
            else f"{name} not evidenced — coverage gap against required skills."
        )
        scorecard.append({"criterion": name, "weight": s["weight"], "score": sub, "note": note})
    return score, scorecard


def build_job(job: dict) -> dict:
    rubric = [
        {
            "id": f"r{i+1}",
            "label": s["name"],
            "description": f"Required {s['level'].replace('-', ' ')} competency for this role.",
            "tag": TAG_BY_LEVEL[s["level"]],
            "category": "Skills",
            "weight": s["weight"],
        }
        for i, s in enumerate(job["requiredSkills"])
    ]
    return {
        "id": job["id"],
        "title": job["title"],
        "department": job["department"],
        "location": job["location"],
        "type": job["type"],
        "status": job["status"],
        "description": job["description"],
        "rubric": rubric,
        "versions": [
            {
                "version": 1,
                "label": "Version 1",
                "status": "Approved",
                "by": "Synthetic pipeline",
                "date": "Aug 1, 2026",
            }
        ],
        "createdAt": job["createdAt"],
    }


def build_candidate(app: dict, person: dict, job: dict) -> dict:
    score, scorecard = derive_score(job, person)
    total_must = sum(1 for s in job["requiredSkills"] if s["level"] == "must-have")
    covered_must = sum(1 for s in job["requiredSkills"] if s["level"] == "must-have" and s["name"] in person["skills"])
    return {
        "id": f"{person['id']}-{app['id']}",
        "jobId": job["id"],
        "name": person["name"],
        "email": person["email"],
        "phone": person["phone"],
        "location": person["location"],
        "source": derive_source(person),
        "tags": derive_tags(person),
        "notes": "",
        "resumeFile": f"{person['id']}.pdf",
        "yearsExp": person["yearsExp"],
        "currentTitle": person["currentTitle"],
        "currentCompany": person["currentCompany"],
        "skills": person["skills"],
        "score": score,
        "shortlisted": score >= 80,
        "decision": "None",
        "pipelineStage": STAGE_BY_STATUS[app["status"]],
        "summary": person["summary"],
        "experience": [
            {"title": e["title"], "company": e["company"], "period": period(e["from"], e["to"])}
            for e in person["experience"]
        ],
        "education": person["education"],
        "certifications": person["certifications"],
        "scorecard": scorecard,
        "strengths": person["strengths"],
        "gaps": person["gaps"],
        "aiNote": f"Screening score {score}/100 — {covered_must} of {total_must} must-have skills covered.",
        "compareVerdict": VERDICT_BY_SCORE(score),
        "appliedAt": app["appliedAt"],
    }


def js_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    jobs = load_many(JOBS_DIR)
    people = load_many(PEOPLE_DIR)
    apps = [json.loads(p.read_text()) for p in sorted(APPS_DIR.glob("*.json"))]

    out_jobs = sorted((build_job(j) for j in jobs.values()), key=lambda j: j["id"])

    out_candidates = [build_candidate(a, people[a["personId"]], jobs[a["jobId"]]) for a in apps]
    out_candidates.sort(key=lambda c: (c["jobId"], -c["score"]))

    lines = [
        "// AUTO-GENERATED by scripts/synthetic/convert/to_frontend_seed.py — do not edit by hand.",
        "// Derived from canonical raw signals in data/synthetic/ (37 jobs, 90 people, 228 applications).",
        "import type { Candidate, Job } from './types';",
        "",
        f"export const jobs: Job[] = {json.dumps(out_jobs, indent=2)};",
        "",
        f"export const candidates: Candidate[] = {json.dumps(out_candidates, indent=2)};",
        "",
    ]
    OUT.write_text("\n".join(lines))
    FRONTEND_OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT.relative_to(ROOT.parent)} and {FRONTEND_OUT.relative_to(ROOT.parent.parent)}: {len(out_jobs)} jobs, {len(out_candidates)} candidates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
