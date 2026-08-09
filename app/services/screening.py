"""Deterministic candidate screening, ported from the frontend scoring lib.

These functions reproduce `frontend/src/lib/scoring.ts` exactly (which was
itself a port of the synthetic pipeline). The backend owns scoring so the
browser only renders results.

Formula (documented so it can be argued with):
    matched_must = Σ weight of Must-have criteria whose label ∈ candidate.skills
    matched_nice = Σ weight of Nice-to-have criteria whose label ∈ candidate.skills
    score        = min(99, round(30 + 65·matched_must/total_must + 5·matched_nice/total_nice))

Python's round() is already half-to-even (banker's rounding), so no pyRound
shim is needed on this side.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from app.services.skill_dictionary import SKILL_DICTIONARY

TAG = Literal["Must-have", "Nice-to-have", "Disqualifying"]
CATEGORY = Literal["Technical Skills", "Soft Skills", "Skills"]

Criteria = Literal["Must-have", "Nice-to-have", "Disqualifying"]


class RubricCriterion(TypedDict):
    id: str
    label: str
    description: str
    tag: TAG
    category: str
    weight: int


class ScorecardRow(TypedDict):
    criterion: str
    weight: int
    score: int
    note: str


class ScreeningResult(TypedDict):
    score: int
    scorecard: list[ScorecardRow]
    ai_note: str
    compare_verdict: str
    shortlisted: bool


def skill_matches(label: str, skills: list[str]) -> bool:
    needle = label.strip().lower()
    if not needle:
        return False
    return any(s.strip().lower() == needle for s in skills)


def derive_score(rubric: list[RubricCriterion], skills: list[str]) -> ScreeningResult:
    must = [r for r in rubric if r["tag"] == "Must-have"]
    nice = [r for r in rubric if r["tag"] == "Nice-to-have"]

    total_must = sum(r["weight"] for r in must) or 1
    total_nice = sum(r["weight"] for r in nice) or 1

    matched_must = sum(r["weight"] for r in must if skill_matches(r["label"], skills))
    matched_nice = sum(r["weight"] for r in nice if skill_matches(r["label"], skills))

    score = min(99, round(30 + 65 * (matched_must / total_must) + 5 * (matched_nice / total_nice)))

    scorecard: list[ScorecardRow] = []
    for r in sorted(rubric, key=lambda r: -r["weight"]):
        hit = skill_matches(r["label"], skills)
        scorecard.append(
            {
                "criterion": r["label"],
                "weight": r["weight"],
                "score": 100 if hit else 35,
                "note": (
                    f"Direct evidence of {r['label']} on resume."
                    if hit
                    else f"{r['label']} not evidenced — coverage gap against required skills."
                ),
            }
        )

    covered = sum(1 for r in must if skill_matches(r["label"], skills))
    total = len(must)
    ai_note = f"Screening score {score}/100 — {covered} of {total} must-have skills covered."
    compare_verdict = "Advance" if score >= 80 else "Maybe" if score >= 55 else "Pass"

    return {
        "score": score,
        "scorecard": scorecard,
        "ai_note": ai_note,
        "compare_verdict": compare_verdict,
        "shortlisted": score >= 80,
    }


def build_strengths(scorecard: list[ScorecardRow]) -> list[str]:
    return [
        f"{row['criterion']} evidenced directly on the resume."
        for row in scorecard
        if row["score"] >= 100
    ]


def build_gaps(scorecard: list[ScorecardRow]) -> list[str]:
    return [
        f"{row['criterion']} not evidenced — coverage gap against required skills."
        for row in scorecard
        if row["score"] < 100
    ]


def extract_skills(text: str, dictionary: list[str] = SKILL_DICTIONARY) -> list[str]:
    """Deterministic keyword extraction, matching the frontend's semantics."""
    lower = f" {text.lower()} "
    hits: list[str] = []
    for skill in dictionary:
        needle = skill.lower()
        in_text = (
            f" {needle} " in lower
            or f" {needle}," in lower
            or f" {needle}." in lower
            or f" {needle};" in lower
            or f" {needle}:" in lower
            or f" {needle}/" in lower
            or (f"{needle} " in lower and needle in lower)
        )
        if in_text:
            hits.append(skill)
    # Multi-word skills first so "React Native" wins over "React".
    hits.sort(key=len, reverse=True)
    return hits


REQUIRED_HINT = re.compile(r"\b(required|must have|must-have|need|needs|experience with|proficiency|expertise)\b", re.I)
DISQUALIFYING_HINT = re.compile(r"\b(no |no, |disqualif|automatic reject|red flag|minimum bar)\b", re.I)

TECHNICAL = {
    "Go", "Python", "Java", "SQL", "TypeScript", "JavaScript", "C#", "Kotlin", "Swift",
    "React", "Vue.js", "Angular", "Next.js", "Node.js", "AWS", "Azure", "GCP",
    "Kubernetes", "Docker", "Terraform", "PostgreSQL", "Redis", "Kafka", "Django",
    "FastAPI", "PyTorch", "TensorFlow",
}
SOFT = {
    "Team Leadership", "Technical Mentorship", "Stakeholder Communication",
    "Agile Delivery", "Hiring & Onboarding", "Performance Management",
}


def category_for(label: str) -> str:
    if label in TECHNICAL:
        return "Technical Skills"
    if label in SOFT:
        return "Soft Skills"
    return "Skills"


def _context_snippet(description: str, idx: int, label: str) -> str:
    """Short, cleaned-up excerpt of the JD around a matched skill, used to make
    each rubric criterion's description reference what was actually written
    instead of one boilerplate sentence repeated for every criterion."""
    start = max(0, idx - 40)
    end = min(len(description), idx + len(label) + 40)
    snippet = re.sub(r"\s+", " ", description[start:end]).strip()
    if start > 0:
        snippet = f"…{snippet}"
    if end < len(description):
        snippet = f"{snippet}…"
    return snippet


def generate_rubric(description: str, dictionary: list[str] = SKILL_DICTIONARY) -> list[RubricCriterion]:
    """Heuristic JD -> rubric generator (mirror of the frontend generateRubric)."""
    candidates: list[tuple[str, str, str]] = []
    for label in extract_skills(description, dictionary):
        idx = description.lower().index(label.lower())
        before = description[max(0, idx - 80) : idx]
        if DISQUALIFYING_HINT.search(before):
            tag: str = "Disqualifying"
        elif REQUIRED_HINT.search(before):
            tag = "Must-have"
        else:
            tag = "Nice-to-have"
        candidates.append((label, tag, _context_snippet(description, idx, label)))

    must = [l for l, t, _ in candidates if t == "Must-have"]
    nice = [l for l, t, _ in candidates if t == "Nice-to-have"]
    disqual = [l for l, t, _ in candidates if t == "Disqualifying"]

    buckets: list[tuple[str, int]] = [(l, 3) for l in must]
    buckets += [(l, 1) for l in nice]
    buckets += [(l, 1) for l in disqual]

    weights: dict[str, int] = {}
    if buckets:
        raw = sum(w for _, w in buckets)
        assigned = 0
        for label, w in buckets:
            share = round(w / raw * 100)
            weights[label] = share
            assigned += share
        drift = 100 - assigned
        if drift:
            largest = max(buckets, key=lambda b: b[1])[0]
            weights[largest] += drift

    rubric: list[RubricCriterion] = []
    for label, tag, snippet in candidates:
        slug = re.sub(r"[^a-z0-9]", "", label, flags=re.I)[:12]
        fallback = (
            "Disqualifying criterion for this role."
            if tag == "Disqualifying"
            else "Required must have competency for this role."
            if tag == "Must-have"
            else "Preferred nice to have competency for this role."
        )
        rubric.append(
            {
                "id": f"r{slug}",
                "label": label,
                "description": f'From the job description: "{snippet}"' if snippet else fallback,
                "tag": tag,
                "category": category_for(label),
                "weight": weights.get(label, 0),
            }
        )
    return rubric
