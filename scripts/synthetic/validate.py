"""Independent verifier for the synthetic dataset.

Deterministic checks (no LLM, no jsonschema dependency — the contract rules are checked
by hand so the verifier never depends on the package that authoring agents may or may not
have installed):

    1. Contract/schema conformance  — required fields, types, enums, patterns, no extra keys
    2. Referential integrity         — every application points at an existing job + person
    3. Coverage                      — >= 5 applications per job; 1..3 per person
    4. Uniqueness                    — emails and phone numbers unique across all people
    5. Timeline sanity               — monotonic, contiguous experience; yearsExp ~= duration
    6. Skill spread per job          — >= 1 applicant covers all must-haves, >= 1 misses one

Usage: python scripts/synthetic/validate.py
Exit code 0 = all checks passed.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "synthetic"
JOBS_DIR = ROOT / "jobs"
PEOPLE_DIR = ROOT / "people"
APPS_DIR = ROOT / "applications"

DOMAINS = {"backend", "frontend", "mobile", "data", "infra", "security", "qa", "architecture", "ai"}
JOB_STATUSES = {"Open", "Draft", "Paused", "Closed"}
SKILL_LEVELS = {"must-have", "nice-to-have", "disqualifying"}
APP_STATUSES = {"Applied", "Screening", "Interview", "Offer", "Rejected"}
ID_PATTERN = re.compile(r"^(job|person|app)-[0-9]{3}-[a-z0-9-]+$")
MONTH_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
MIN_APPS_PER_JOB = 5
MAX_APPS_PER_PERSON = 3

ERRORS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def check_required(obj: dict, required: list[str], label: str) -> None:
    for key in required:
        if key not in obj:
            err(f"{label}: missing required field '{key}'")


def check_no_extra(obj: dict, allowed: set[str], label: str) -> None:
    for key in obj:
        if key not in allowed:
            err(f"{label}: unexpected field '{key}' (contract is additionalProperties: false)")


def check_enums(obj: dict, field: str, allowed: set[str], label: str) -> None:
    if field in obj and obj[field] not in allowed:
        err(f"{label}: '{field}' = {obj[field]!r} not in {sorted(allowed)}")


def check_id(obj: dict, label: str) -> None:
    if "id" in obj and not ID_PATTERN.match(obj["id"]):
        err(f"{label}: id {obj['id']!r} does not match {ID_PATTERN.pattern}")


def months_since(start_ym: str, end_ym: str | None) -> float:
    """Rough contiguous months between two YYYY-MM points (null end = now)."""
    start = date(int(start_ym[:4]), int(start_ym[5:7]), 1)
    end = date.today() if end_ym is None else date(int(end_ym[:4]), int(end_ym[5:7]), 1)
    return (end.year - start.year) * 12 + (end.month - start.month)


def validate_job(path: Path) -> dict:
    data = json.loads(path.read_text())
    check_id(data, path.name)
    check_required(data, ["id", "title", "domain", "department", "location", "type", "status",
                          "description", "seniority", "yearsRequired", "requiredSkills", "createdAt"], path.name)
    check_no_extra(data, {"id", "title", "domain", "department", "location", "type", "status",
                          "description", "seniority", "yearsRequired", "requiredSkills", "createdAt"}, path.name)
    check_enums(data, "domain", DOMAINS, path.name)
    check_enums(data, "type", {"Full-time", "Contract", "Hybrid"}, path.name)
    check_enums(data, "status", JOB_STATUSES, path.name)
    check_enums(data, "seniority", {"Junior", "Mid", "Senior", "Staff"}, path.name)
    if not isinstance(data.get("yearsRequired"), int) or data["yearsRequired"] < 0:
        err(f"{path.name}: yearsRequired must be a non-negative int")
    total_weight = 0
    for i, s in enumerate(data.get("requiredSkills", [])):
        label = f"{path.name}.requiredSkills[{i}]"
        check_required(s, ["name", "level", "weight"], label)
        check_no_extra(s, {"name", "level", "weight"}, label)
        check_enums(s, "level", SKILL_LEVELS, label)
        if not isinstance(s.get("weight"), int) or not (1 <= s["weight"] <= 100):
            err(f"{label}: weight must be int in 1..100")
        total_weight += s.get("weight", 0)
    if data.get("requiredSkills") and total_weight != 100:
        err(f"{path.name}: requiredSkills weights sum to {total_weight}, expected 100")
    return data


def validate_person(path: Path) -> dict:
    data = json.loads(path.read_text())
    check_id(data, path.name)
    check_required(data, ["id", "name", "email", "phone", "location", "yearsExp", "currentTitle",
                          "currentCompany", "skills", "experience", "education", "certifications",
                          "summary", "strengths", "gaps", "resumeText", "primaryDomain"], path.name)
    check_no_extra(data, {"id", "name", "email", "phone", "location", "yearsExp", "currentTitle",
                          "currentCompany", "skills", "experience", "education", "certifications",
                          "summary", "strengths", "gaps", "resumeText", "primaryDomain"}, path.name)
    check_enums(data, "primaryDomain", DOMAINS, path.name)
    if not isinstance(data.get("yearsExp"), int) or not (0 <= data["yearsExp"] <= 35):
        err(f"{path.name}: yearsExp must be int in 0..35")
    if not isinstance(data.get("email"), str) or "@" not in data["email"]:
        err(f"{path.name}: email not a string containing '@'")

    exp = data.get("experience", [])
    prev_end: str | None = None
    months = 0.0
    for i, e in enumerate(exp):
        label = f"{path.name}.experience[{i}]"
        check_required(e, ["title", "company", "from", "to"], label)
        check_no_extra(e, {"title", "company", "from", "to"}, label)
        for f in ("from",):
            if not MONTH_PATTERN.match(e.get("from", "")):
                err(f"{label}.from = {e.get('from')!r} not YYYY-MM")
        to = e.get("to")
        if to is not None and not MONTH_PATTERN.match(to):
            err(f"{label}.to = {to!r} not YYYY-MM (or null)")
        # monotonic + no unexplained gaps (> 3 months between roles is flagged;
        # 1-month notice-period transitions are normal and ignored)
        f = e.get("from", "")
        if prev_end is not None:
            if f < prev_end:
                err(f"{label}: starts {f} before previous role ended {prev_end}")
            elif months_since(prev_end, f) > 3:
                err(f"{label}: unexplained gap of {months_since(prev_end, f):.0f} months between {prev_end} and {f}")
        prev_end = to or None
        months += months_since(f, to)
    years_est = round(months / 12, 1)
    if exp and abs(years_est - data.get("yearsExp", 0)) > 1.5:
        err(f"{path.name}: yearsExp {data['yearsExp']} ~= experience sum {years_est}y (diff > 1.5)")

    if not isinstance(data.get("skills"), list) or len(data["skills"]) < 3:
        err(f"{path.name}: skills must be a list of >= 3")
    return data


def validate_application(path: Path, person_ids: set[str], job_ids: set[str]) -> dict:
    data = json.loads(path.read_text())
    check_id(data, path.name)
    check_required(data, ["id", "personId", "jobId", "appliedAt", "status"], path.name)
    check_no_extra(data, {"id", "personId", "jobId", "appliedAt", "status"}, path.name)
    check_enums(data, "status", APP_STATUSES, path.name)
    if data["personId"] not in person_ids:
        err(f"{path.name}: personId {data['personId']} does not exist")
    if data["jobId"] not in job_ids:
        err(f"{path.name}: jobId {data['jobId']} does not exist")
    return data


def main() -> int:
    jobs = {d["id"]: d for d in (validate_job(p) for p in sorted(JOBS_DIR.glob("*.json")))}
    people = {d["id"]: d for d in (validate_person(p) for p in sorted(PEOPLE_DIR.glob("*.json")))}
    apps = [validate_application(p, set(people), set(jobs)) for p in sorted(APPS_DIR.glob("*.json"))]

    # Uniqueness
    emails = defaultdict(list)
    phones = defaultdict(list)
    for pid, d in people.items():
        emails[d["email"]].append(pid)
        phones[d["phone"]].append(pid)
    for value, owners in {**emails, **phones}.items():
        if len(owners) > 1:
            err(f"duplicate email/phone {value!r} shared by {owners}")

    # Coverage
    per_job = defaultdict(list)
    per_person = defaultdict(list)
    for a in apps:
        per_job[a["jobId"]].append(a)
        per_person[a["personId"]].append(a)
    for jid, a in per_job.items():
        if len(a) < MIN_APPS_PER_JOB:
            err(f"job {jid}: {len(a)} applications < {MIN_APPS_PER_JOB}")
    for pid, a in per_person.items():
        if not (1 <= len(a) <= MAX_APPS_PER_PERSON):
            err(f"person {pid}: {len(a)} applications (expected 1..{MAX_APPS_PER_PERSON})")

    # Skill spread per job: at least one full-must-have cover, at least one miss.
    for jid, job in jobs.items():
        must_haves = {s["name"] for s in job["requiredSkills"] if s["level"] == "must-have"}
        apps_here = per_job.get(jid, [])
        covers = misses = 0
        for a in apps_here:
            person = people[a["personId"]]
            skills = set(person["skills"])
            missing = must_haves - skills
            if not missing:
                covers += 1
            else:
                misses += 1
        if covers < 1:
            err(f"job {jid}: no applicant covers all {len(must_haves)} must-haves (need >= 1 strong fit)")
        if misses < 1:
            err(f"job {jid}: every applicant covers all must-haves (need >= 1 deliberate weak/mid fit)")

    if ERRORS:
        print(f"VALIDATION FAILED — {len(ERRORS)} problem(s):")
        for e in ERRORS:
            print(f"  ✗ {e}")
        return 1
    print(f"VALIDATION PASSED — {len(jobs)} jobs, {len(people)} people, {len(apps)} applications, 0 problems.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
