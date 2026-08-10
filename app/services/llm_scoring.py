"""Shared JSON-response handling for the two LLM-as-judge call sites
(candidate_judge.py scoring a résumé profile, interview_evaluator.py scoring
a transcript — M2 and M5 respectively). Extracted once both existed and
worked independently (see M5 plan's sequencing note) rather than built as a
speculative shared abstraction on day one — this is the same discipline
candidate_judge.py itself followed relative to screening.py.
"""
from app.services.llm_client import LLMError
from app.services.screening import RubricCriterion, ScorecardRow


def strip_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return cleaned


def clamp_int(value: object, lo: int, hi: int, default: int = 0) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def coerce_scorecard(
    rubric: list[RubricCriterion], llm_scorecard: object, source_label: str = "AI judge"
) -> list[ScorecardRow]:
    """The one piece of logic that must not be duplicated: never trust the LLM's weight or
    an incomplete scorecard. An incomplete scorecard is not an honest partial result — raises
    LLMError rather than silently proceeding, same standard question_generator.py holds
    itself to for malformed output generally."""
    llm_rows = {
        str(row.get("criterion", "")).strip().lower(): row
        for row in (llm_scorecard if isinstance(llm_scorecard, list) else [])
        if isinstance(row, dict)
    }
    scorecard: list[ScorecardRow] = []
    for criterion in rubric:
        row = llm_rows.get(criterion["label"].strip().lower())
        if row is None:
            raise LLMError(f"{source_label} response is missing a scorecard entry for '{criterion['label']}'")
        scorecard.append(
            {
                "criterion": criterion["label"],
                # weight always comes from the rubric, never the LLM — guards against a
                # hallucinated weight that doesn't sum right.
                "weight": criterion["weight"],
                "score": clamp_int(row.get("score"), 0, 100),
                "note": str(row.get("note", "")).strip() or f"{source_label}: {criterion['label']}.",
            }
        )
    return scorecard
