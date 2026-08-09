"""LLM-based interview question generation (M3).

Pattern-matches resume_parser.py's parse_resume: one chat_completion call,
prompt asks for JSON only, strip markdown fences, json.loads. Unlike
parse_resume, a malformed response is NOT swallowed into a fallback object —
question generation has no honest partial result, so a bad response raises
LLMError and the router turns that into a clear 502 instead of silently
returning zero questions.
"""
import json

from app.models.candidate import Candidate
from app.services.llm_client import LLMError, chat_completion

QUESTION_TYPES = {"Technical", "Behavioral", "System Design", "Culture"}
DIFFICULTIES = {"Easy", "Medium", "Hard"}

GENERATION_PROMPT = """You are an expert technical interviewer. Write {count} interview \
questions for the role below and return ONLY a valid JSON array (no markdown fences, no \
commentary) of objects shaped exactly like:

{{"prompt": string, "type": "Technical" | "Behavioral" | "System Design" | "Culture", \
"difficulty": "Easy" | "Medium" | "Hard"}}

Mix all four question types and all three difficulty levels — don't make every question the \
same type or difficulty. Each question must be answerable by talking, not by writing code.

Job title: {job_title}
Job description:
---
{job_description}
---
{candidate_block}
"""

CANDIDATE_BLOCK_TEMPLATE = """
This interview is for a specific candidate — reference their actual background where it's \
relevant (a named project, a listed skill, their current role) instead of staying generic. \
Candidate profile:
---
{candidate_profile}
---
"""

REGENERATE_PROMPT = """You are an expert technical interviewer. Write ONE replacement interview \
question for the role below, matching this exact difficulty: "{difficulty}" and this exact \
type: "{type}". Return ONLY a valid JSON object (no markdown fences, no commentary) shaped \
exactly like:

{{"prompt": string, "type": "{type}", "difficulty": "{difficulty}"}}

The question must be answerable by talking, not by writing code, and must not duplicate any of \
these existing questions:
{other_prompts}

Job title: {job_title}
Job description:
---
{job_description}
---
{candidate_block}
"""


def build_candidate_profile(candidate: Candidate) -> str:
    lines = [f"{candidate.current_title} at {candidate.current_company} ({candidate.years_exp} years experience)"]
    if candidate.summary:
        lines.append(candidate.summary)
    if candidate.skills:
        lines.append("Skills: " + ", ".join(candidate.skills))
    for exp in candidate.experience[:3]:
        title = exp.get("title", "")
        company = exp.get("company", "")
        highlights = exp.get("highlights") or []
        entry = f"- {title} at {company}"
        if highlights:
            entry += ": " + "; ".join(highlights[:2])
        lines.append(entry)
    return "\n".join(lines)


def _strip_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return cleaned


def _coerce_question(item: dict, question_id: str) -> dict:
    prompt = str(item.get("prompt", "")).strip()
    if not prompt:
        raise LLMError(f"Generated question {question_id} has no prompt text")
    q_type = item.get("type") if item.get("type") in QUESTION_TYPES else "Behavioral"
    difficulty = item.get("difficulty") if item.get("difficulty") in DIFFICULTIES else "Medium"
    return {"id": question_id, "prompt": prompt, "type": q_type, "difficulty": difficulty}


async def generate_questions(
    job_title: str,
    job_description: str,
    candidate_profile: str | None = None,
    count: int = 10,
) -> list[dict]:
    candidate_block = CANDIDATE_BLOCK_TEMPLATE.format(candidate_profile=candidate_profile) if candidate_profile else ""
    prompt = GENERATION_PROMPT.format(
        count=count, job_title=job_title, job_description=job_description, candidate_block=candidate_block
    )
    raw = await chat_completion([{"role": "user", "content": prompt}])

    try:
        parsed = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise LLMError(f"Question generation returned invalid JSON: {e}") from e

    if not isinstance(parsed, list) or not (1 <= len(parsed) <= 20):
        raise LLMError(f"Question generation returned an unusable question count: {len(parsed) if isinstance(parsed, list) else 'not a list'}")

    questions = [_coerce_question(item, f"q{i + 1}") for i, item in enumerate(parsed[:12])]
    return questions


async def regenerate_question(
    job_title: str,
    job_description: str,
    candidate_profile: str | None,
    existing: dict,
    others: list[dict],
) -> dict:
    candidate_block = CANDIDATE_BLOCK_TEMPLATE.format(candidate_profile=candidate_profile) if candidate_profile else ""
    other_prompts = "\n".join(f"- {q['prompt']}" for q in others) or "(none)"
    prompt = REGENERATE_PROMPT.format(
        difficulty=existing.get("difficulty", "Medium"),
        type=existing.get("type", "Behavioral"),
        other_prompts=other_prompts,
        job_title=job_title,
        job_description=job_description,
        candidate_block=candidate_block,
    )
    raw = await chat_completion([{"role": "user", "content": prompt}])

    try:
        parsed = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise LLMError(f"Question regeneration returned invalid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise LLMError("Question regeneration did not return a single object")

    return _coerce_question(parsed, existing["id"])
