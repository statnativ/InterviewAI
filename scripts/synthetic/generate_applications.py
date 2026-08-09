"""Generate the applications join layer for the synthetic dataset.

Reads jobs/ + people/ and produces applications/ plus a coverage summary.
Deterministic — the assignment is algorithmic but fully reproducible:

    * the 16 pilot applications are preserved verbatim (the human-reviewed contract)
    * the CROSS_DOMAIN edges are explicit (from scale_spec.md; every edge is mandatory)
    * every NEW job (job-004..037) is assigned MIN_PER_JOB applicants drawn from its
      domain pool, ranked by must-have coverage so each job gets >= 1 strong cover
      (all must-haves) and >= 1 deliberate weak/mid miss
    * per-person cap MAX_PER_PERSON is respected; pilot people may also appear on
      new jobs in their own domain when the pool needs filler

Invariants enforced:
    * every job has >= MIN_PER_JOB applications
    * every person has 1..=MAX_PER_PERSON applications
    * every referenced personId/jobId exists on disk

Usage: python scripts/synthetic/generate_applications.py
"""

from __future__ import annotations

import json
import sys
import zlib
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "synthetic"
JOBS_DIR = ROOT / "jobs"
PEOPLE_DIR = ROOT / "people"
APPS_DIR = ROOT / "applications"

MIN_PER_JOB = 5
MAX_PER_PERSON = 3

# Human-reviewed pilot contract (kept verbatim from the pilot run).
PILOT_APPLICATIONS = [
    ("person-001-aisha-rahman", "job-001-senior-backend-go", "Interview"),
    ("person-002-diego-fernandez", "job-001-senior-backend-go", "Screening"),
    ("person-003-priya-nataraj", "job-001-senior-backend-go", "Applied"),
    ("person-004-marcus-bell", "job-001-senior-backend-go", "Rejected"),
    ("person-005-elena-petrova", "job-001-senior-backend-go", "Applied"),
    ("person-006-hannah-park", "job-002-senior-frontend-react", "Interview"),
    ("person-007-liam-oconnor", "job-002-senior-frontend-react", "Screening"),
    ("person-008-meera-iyer", "job-002-senior-frontend-react", "Applied"),
    ("person-009-noah-williams", "job-002-senior-frontend-react", "Rejected"),
    ("person-010-isabella-rossi", "job-002-senior-frontend-react", "Applied"),
    ("person-011-raj-patel", "job-003-data-engineer", "Interview"),
    ("person-012-yuki-tanaka", "job-003-data-engineer", "Screening"),
    ("person-013-carlos-mendez", "job-003-data-engineer", "Applied"),
    ("person-014-fatima-al-sayed", "job-003-data-engineer", "Applied"),
    ("person-015-james-whitfield", "job-003-data-engineer", "Rejected"),
    ("person-003-priya-nataraj", "job-003-data-engineer", "Applied"),
]

# Explicit cross-domain edges from scale_spec.md (person-003->job-003 already exists in the
# pilot block above). Each of these people is deducted a slot from their in-domain pool.
CROSS_DOMAIN = [
    ("person-005-elena-petrova", "job-022-cloud-engineer-aws"),
    ("person-016-lena-fischer", "job-003-data-engineer"),
    ("person-017-omar-haddad", "job-015-data-analyst"),
    ("person-024-mateo-alvarez", "job-032-staff-distributed"),
    ("person-029-freya-nielsen", "job-035-genai-app-dev"),
    ("person-082-yasmine-benali", "job-017-ml-engineer"),
    ("person-049-lucas-silva", "job-018-ml-platform"),
    ("person-018-vikram-singh", "job-028-sdet"),
    ("person-084-charlotte-dubois", "job-005-backend-python"),
]


def load(directory: Path) -> dict[str, dict]:
    return {d["id"]: d for d in (json.loads(p.read_text()) for p in sorted(directory.glob("*.json")))}


def must_haves(job: dict) -> set[str]:
    return {s["name"] for s in job["requiredSkills"] if s["level"] == "must-have"}


def covered_count(person: dict, job: dict) -> int:
    return len(must_haves(job) & set(person["skills"]))


def derive_status(person_id: str, job_id: str, covered: int, total: int) -> str:
    """Deterministic status from must-have coverage; sprinkles Offer/Rejected variety."""
    ratio = covered / total if total else 0.0
    parity = zlib.crc32(f"{person_id}|{job_id}".encode()) % 10
    if ratio >= 1.0:
        return "Offer" if parity < 2 else "Interview"
    if ratio >= 0.75:
        return "Interview" if parity < 4 else "Screening"
    if ratio >= 0.5:
        return "Screening" if parity < 5 else "Applied"
    return "Applied" if parity < 4 else "Rejected"


def main() -> int:
    jobs = load(JOBS_DIR)
    people = load(PEOPLE_DIR)

    # Seed the planned set with the pilot contract.
    planned: list[tuple[str, str, str]] = list(PILOT_APPLICATIONS)
    # person -> set of job ids already committed (pilot + cross-domain)
    committed: dict[str, set[str]] = defaultdict(set)
    for pid, jid, _ in PILOT_APPLICATIONS:
        committed[pid].add(jid)
    for pid, jid in CROSS_DOMAIN:
        if pid not in people or jid not in jobs:
            print(f"ERROR: cross-domain edge references unknown {pid} or {jid}")
            return 1
        if len(committed[pid]) >= MAX_PER_PERSON:
            print(f"ERROR: cross-domain edge pushes {pid} past {MAX_PER_PERSON} apps")
            return 1
        committed[pid].add(jid)
        planned.append((pid, jid, derive_status(pid, jid, covered_count(people[pid], jobs[jid]), len(must_haves(jobs[jid])))))

    # Group new jobs by domain.
    by_domain: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    pilot_jobs = {jid for _, jid, _ in PILOT_APPLICATIONS}
    for jid, job in sorted(jobs.items()):
        if jid not in pilot_jobs:
            by_domain[job["domain"]].append((jid, job))

    # PASS 1 — reserve each job's strongest candidate so every job is guaranteed a
    # full must-have cover. One person is the top fit for at most one job in a domain,
    # and each top fit is distinct, so this reservation never starves another job.
    strong_by_job: dict[str, dict] = {}
    for domain, job_list in sorted(by_domain.items()):
        pool = [p for p in people.values() if p["primaryDomain"] == domain]
        for jid, job in sorted(job_list):
            eligible = [
                p for p in pool
                if jid not in committed[p["id"]] and len(committed[p["id"]]) < MAX_PER_PERSON
            ]
            eligible.sort(key=lambda p: (-covered_count(p, job), p["id"]))
            if eligible:
                strong = eligible[0]
                strong_by_job[jid] = strong
                committed[strong["id"]].add(jid)
                planned.append((strong["id"], jid, derive_status(strong["id"], jid, covered_count(strong, job), len(must_haves(job)))))

    # PASS 2 — fill every job to MIN_PER_JOB: deliberate miss first (lowest coverage that
    # misses a must-have), then the remaining highest-coverage eligible people.
    for domain, job_list in sorted(by_domain.items()):
        pool = [p for p in people.values() if p["primaryDomain"] == domain]
        for jid, job in sorted(job_list):
            total = len(must_haves(job))
            eligible = [
                p for p in pool
                if jid not in committed[p["id"]] and len(committed[p["id"]]) < MAX_PER_PERSON
            ]
            eligible.sort(key=lambda p: (-covered_count(p, job), p["id"]))
            weak = next((p for p in reversed(eligible) if covered_count(p, job) < total), None)

            # Filler order balances load: people with the fewest apps so far get picked
            # first (ties broken by coverage), so no one gets capped out early.
            fillers = sorted(eligible, key=lambda p: (len(committed[p["id"]]), -covered_count(p, job), p["id"]))
            chosen: list[dict] = []
            if weak is not None:
                chosen.append(weak)
            for p in fillers:
                if len(chosen) >= MIN_PER_JOB:
                    break
                if p not in chosen:
                    chosen.append(p)

            # The strong cover from PASS 1 already counts toward this job.
            already = 1 if strong_by_job.get(jid) else 0
            if len(chosen) + already < MIN_PER_JOB:
                print(f"ERROR: job {jid}: only {len(chosen) + already} eligible applicants (< {MIN_PER_JOB})")
                return 1

            for p in chosen:
                committed[p["id"]].add(jid)
                planned.append((p["id"], jid, derive_status(p["id"], jid, covered_count(p, job), total)))

    # Validate invariants before materializing.
    per_job: dict[str, int] = defaultdict(int)
    per_person: dict[str, int] = defaultdict(int)
    for pid, jid, _ in planned:
        per_job[jid] += 1
        per_person[pid] += 1
    errors = []
    for jid, n in per_job.items():
        if n < MIN_PER_JOB:
            errors.append(f"job {jid} has {n} apps (< {MIN_PER_JOB})")
    for pid, n in per_person.items():
        if not (1 <= n <= MAX_PER_PERSON):
            errors.append(f"person {pid} has {n} apps (expected 1..{MAX_PER_PERSON})")
    for pid, jid, _ in planned:
        if pid not in people:
            errors.append(f"unknown person {pid}")
        if jid not in jobs:
            errors.append(f"unknown job {jid}")
    if errors:
        print("\n".join(errors))
        return 1

    # Materialize files. appliedAt spreads deterministically from 2026-06-01.
    APPS_DIR.mkdir(exist_ok=True)
    for old in APPS_DIR.glob("*.json"):
        old.unlink()

    start = date(2026, 6, 1)
    for n, (pid, jid, status) in enumerate(sorted(planned, key=lambda t: (t[1], t[0])), start=1):
        app_id = f"app-{n:03d}-{pid.removeprefix('person-')}"
        record = {
            "id": app_id,
            "personId": pid,
            "jobId": jid,
            "appliedAt": (start + timedelta(days=n - 1)).isoformat(),
            "status": status,
        }
        (APPS_DIR / f"{app_id}.json").write_text(json.dumps(record, indent=2) + "\n")

    print(f"Wrote {len(planned)} applications across {len(per_job)} jobs, {len(per_person)} people.")
    for jid in sorted(jobs):
        print(f"  {jid}: {per_job[jid]} apps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
