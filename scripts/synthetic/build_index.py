"""Regenerate data/synthetic/index.json — a human-readable registry + coverage report.

Derived straight from the folders, so it can never drift out of sync.

Usage: python scripts/synthetic/build_index.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "synthetic"
JOBS_DIR = ROOT / "jobs"
PEOPLE_DIR = ROOT / "people"
APPS_DIR = ROOT / "applications"


def main() -> int:
    jobs = {d["id"]: d for d in (json.loads(p.read_text()) for p in sorted(JOBS_DIR.glob("*.json")))}
    people = {d["id"]: d for d in (json.loads(p.read_text()) for p in sorted(PEOPLE_DIR.glob("*.json")))}
    apps = [json.loads(p.read_text()) for p in sorted(APPS_DIR.glob("*.json"))]

    per_job: dict[str, list[dict]] = {jid: [] for jid in jobs}
    for a in apps:
        per_job.setdefault(a["jobId"], []).append(a)

    job_index = []
    for jid, job in sorted(jobs.items()):
        aps = sorted(per_job.get(jid, []), key=lambda a: a["personId"])
        job_index.append(
            {
                "id": jid,
                "title": job["title"],
                "domain": job["domain"],
                "seniority": job["seniority"],
                "applicationCount": len(aps),
                "applicants": [
                    {
                        "personId": a["personId"],
                        "name": people[a["personId"]]["name"],
                        "status": a["status"],
                    }
                    for a in aps
                ],
            }
        )

    index = {
        "generatedAt": "2026-08-08",
        "summary": {
            "jobs": len(jobs),
            "people": len(people),
            "applications": len(apps),
            "averageApplicationsPerJob": round(len(apps) / max(len(jobs), 1), 1),
        },
        "jobs": job_index,
    }
    (ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"Wrote index.json: {index['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
