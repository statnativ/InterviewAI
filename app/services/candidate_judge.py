"""LLM-as-judge candidate scoring (M2, second half).

Pattern-matches question_generator.py: one chat_completion call, prompt asks
for JSON only, strip markdown fences, json.loads, no silent partial fallback
on a malformed response — an incomplete scorecard is not an honest result,
so a bad response raises LLMError and the router turns that into a clear 502.

Additive to, not a replacement for, the deterministic scorer in screening.py
— derive_score stays the free/instant default for candidate creation and
resume upload; this is only reachable via an explicit, recruiter-triggered
action (POST /candidates/{app_id}/judge), since it's a paid call unlike the
keyword-matching path. Returns the exact same ScreeningResult shape
derive_score does, so callers/frontend treat both paths identically.
"""
import json
from typing import TypedDict

from app.models.candidate import Candidate
from app.services.llm_client import LLMError, chat_completion
from app.services.screening import RubricCriterion, ScorecardRow, ScreeningResult


class JudgeResult(ScreeningResult):
    """ScreeningResult plus strengths/gaps. The deterministic path
    (screening.py) doesn't carry these on its result — the router derives
    them separately via build_strengths/build_gaps, which assume the
    binary 100/35 scoring convention derive_score always produces. The LLM
    judge's scores are continuous (0-100, reasoned), so that same
    100-or-nothing threshold would almost never fire — the judge supplies
    strengths/gaps directly instead, superset of ScreeningResult rather
    than identical to it."""

    strengths: list[str]
    gaps: list[str]

JUDGE_PROMPT = """You are an expert technical recruiter scoring a candidate against a job's \
rubric. Return ONLY a valid JSON object (no markdown fences, no commentary) shaped exactly like:

{{"score": int (0-99), "compare_verdict": "Advance" | "Maybe" | "Pass", "ai_note": string, \
"strengths": [string, ...], "gaps": [string, ...], \
"scorecard": [{{"criterion": string, "score": int (0-100), "note": string}}, ...]}}

Score each rubric criterion below on its own merits — reason about the depth and relevance of \
the candidate's actual experience, don't just check for keyword presence. Include exactly one \
scorecard entry per rubric criterion listed below, using the criterion's exact label. The \
top-level "score" should reflect overall fit, weighted toward Must-have criteria over \
Nice-to-have ones.

Job title: {job_title}
Job description:
---
{job_description}
---
Rubric (label — tag — weight%):
{rubric_block}

Candidate profile:
---
{candidate_profile}
---
"""


def build_scoring_profile(candidate: Candidate) -> str:
    """Full structured profile for the judge prompt — everything derive_score
    never looks at (experience depth, summary, education, certifications),
    not just candidate.skills. Deliberately omits candidate.name, same
    reasoning question_generator.py already applies to its own profile
    builder: this data doesn't need a name to be useful, and a name is one
    obvious surface for bias in a scoring feature specifically. A separate
    function from question_generator.build_candidate_profile on purpose —
    that one caps experience at 3 entries and skips education/certifications,
    which matter here in a way they don't for writing interview questions."""
    lines = [f"{candidate.current_title} at {candidate.current_company} ({candidate.years_exp} years experience)"]
    if candidate.summary:
        lines.append(candidate.summary)
    if candidate.skills:
        lines.append("Skills: " + ", ".join(candidate.skills))
    for exp in candidate.experience:
        title = exp.get("title", "")
        company = exp.get("company", "")
        highlights = exp.get("highlights") or []
        entry = f"- {title} at {company}"
        if highlights:
            entry += ": " + "; ".join(highlights)
        lines.append(entry)
    if candidate.education:
        lines.append(f"Education: {candidate.education}")
    if candidate.certifications:
        lines.append(f"Certifications: {candidate.certifications}")
    return "\n".join(lines)


def _strip_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return cleaned


def _coerce_result(parsed: dict, rubric: list[RubricCriterion]) -> JudgeResult:
    # score: never trust the raw value even if present and well-typed —
    # clamp to the same [0, 99] ceiling derive_score already enforces.
    try:
        score = max(0, min(99, int(parsed.get("score", 0))))
    except (TypeError, ValueError):
        score = 0

    verdict = parsed.get("compare_verdict")
    if verdict not in ("Advance", "Maybe", "Pass"):
        # Safe fallback: derive it from the (already-clamped) score using
        # derive_score's own thresholds, rather than trusting free text.
        verdict = "Advance" if score >= 80 else "Maybe" if score >= 55 else "Pass"

    llm_rows = {
        str(row.get("criterion", "")).strip().lower(): row
        for row in parsed.get("scorecard", [])
        if isinstance(row, dict)
    }
    scorecard: list[ScorecardRow] = []
    for criterion in rubric:
        row = llm_rows.get(criterion["label"].strip().lower())
        if row is None:
            # An incomplete scorecard is not an honest partial result —
            # same standard question_generator.py holds itself to.
            raise LLMError(f"AI judge response is missing a scorecard entry for '{criterion['label']}'")
        try:
            row_score = max(0, min(100, int(row.get("score", 0))))
        except (TypeError, ValueError):
            row_score = 0
        scorecard.append(
            {
                "criterion": criterion["label"],
                # weight always comes from the rubric, never the LLM — guards
                # against a hallucinated weight that doesn't sum right, same
                # reason derive_score computes weight from the rubric.
                "weight": criterion["weight"],
                "score": row_score,
                "note": str(row.get("note", "")).strip() or f"AI-judged: {criterion['label']}.",
            }
        )

    ai_note = str(parsed.get("ai_note", "")).strip() or f"AI judge score {score}/100."
    strengths = [str(s) for s in parsed.get("strengths", [])] if isinstance(parsed.get("strengths"), list) else []
    gaps = [str(g) for g in parsed.get("gaps", [])] if isinstance(parsed.get("gaps"), list) else []

    return {
        "score": score,
        "scorecard": scorecard,
        "ai_note": ai_note,
        "compare_verdict": verdict,
        # Computed here, not read from the LLM, so "Shortlisted" means the
        # same threshold regardless of which method produced the score.
        "shortlisted": score >= 80,
        "strengths": strengths,
        "gaps": gaps,
    }


async def judge_candidate(
    job_title: str,
    job_description: str,
    rubric: list[RubricCriterion],
    candidate_profile: str,
) -> JudgeResult:
    rubric_block = "\n".join(f"- {r['label']} — {r['tag']} — {r['weight']}%" for r in rubric)
    prompt = JUDGE_PROMPT.format(
        job_title=job_title,
        job_description=job_description,
        rubric_block=rubric_block,
        candidate_profile=candidate_profile,
    )
    raw = await chat_completion([{"role": "user", "content": prompt}])

    try:
        parsed = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise LLMError(f"AI judge returned invalid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise LLMError("AI judge did not return a single JSON object")

    return _coerce_result(parsed, rubric)
