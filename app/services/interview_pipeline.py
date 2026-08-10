"""Cascaded voice interview pipeline: STT -> LLM -> TTS.

This is the "brain" of the async audio interview: given a running
conversation history and the candidate's latest spoken answer, it transcribes
the answer, asks the interviewer LLM what to say next, and synthesizes that
reply back to audio. History is a plain list of chat messages (system/user/
assistant) — the LLM is the only thing that needs to "remember" the
conversation, so that list *is* the session state.

M4: the interviewer asks the interview's own curated questions (M3 —
Interview.questions), in order, rather than deciding freely what to ask —
this reuses the entire question-authoring feature for Voice mode and gives a
real, detectable end-of-interview signal (COMPLETION_SENTINEL) instead of an
open-ended conversation with no natural stopping point.
"""

from dataclasses import dataclass, field

from app.config import settings
from app.services.llm_client import chat_completion
from app.services.stt_client import transcribe
from app.services.tts_client import synthesize

# The exact token the interviewer is instructed to emit once the last question (and its
# optional follow-up) has been answered. Stripped from ai_text before it's shown/spoken to
# the candidate or stored in history — see strip_completion_sentinel below. Must be applied
# BEFORE synthesize() is called in start_interview/run_turn, not after — otherwise TTS would
# literally speak the token out loud.
COMPLETION_SENTINEL = "[INTERVIEW_COMPLETE]"

SYSTEM_PROMPT_TEMPLATE = """You are an AI interviewer conducting a first-round screening interview for the \
following role. You must ask the candidate the questions listed below, one at a time, in the exact order given \
— do not skip, reorder, or invent additional questions. For each question you may ask at most one natural \
follow-up based on what the candidate actually says before moving on to the next question.

Job title: {job_title}
Job description: {jd_text}

Questions to ask, in order:
{questions_block}

Keep every question and follow-up concise (2-3 sentences max, spoken aloud). Once the candidate has answered the \
final question above (and its one optional follow-up, if you asked one), thank them briefly for their time and \
end your message with the exact literal text {sentinel} on its own, with nothing after it. Do not include that \
text at any other point in the interview.

Start the interview now by asking the first question. Respond with ONLY what you would say out loud — no \
preamble, no labels like "Question 1:".
"""


def _format_questions_block(questions: list[str]) -> str:
    return "\n".join(f"{i}. {q}" for i, q in enumerate(questions, start=1))


def build_system_prompt(job_title: str, jd_text: str, questions: list[str]) -> str:
    """Public so the interview-sessions router can rebuild an identical system message when
    reconstructing `history` from persisted turns for turn 2+ — the message itself is never
    stored on an InterviewTurn row, only transcript/ai_text are."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        job_title=job_title,
        jd_text=jd_text,
        questions_block=_format_questions_block(questions),
        sentinel=COMPLETION_SENTINEL,
    )


def strip_completion_sentinel(ai_text: str) -> tuple[str, bool]:
    """Detects the interviewer's end-of-interview signal and strips it before the text is
    shown/spoken to the candidate. Returns (cleaned_text, is_complete). Pure text processing —
    callers are responsible for acting on is_complete (e.g. flipping session status)."""
    if COMPLETION_SENTINEL in ai_text:
        return ai_text.replace(COMPLETION_SENTINEL, "").rstrip(), True
    return ai_text, False


def bound_history(history: list[dict], max_turns: int) -> list[dict]:
    """IA-004: caps how much conversation gets sent to the LLM each turn. Always keeps the
    system prompt (index 0) plus the most recent `max_turns` messages, dropping the oldest
    first. Pure function of the list passed in — does not read the DB itself; callers
    (the interview-sessions router) reconstruct `history` from persisted turns and bound it
    here before calling run_turn, so run_turn's own signature needs no refactor."""
    if len(history) <= 1 + max_turns:
        return history
    return [history[0], *history[-max_turns:]]


@dataclass
class InterviewTurnResult:
    transcript: str | None  # candidate's transcribed answer; None for the opening turn
    ai_text: str
    ai_audio: bytes
    is_complete: bool
    history: list[dict] = field(default_factory=list)


async def start_interview(job_title: str, jd_text: str, questions: list[str]) -> InterviewTurnResult:
    """Seed a new interview: build the system prompt (with the interview's own curated
    questions) and get the opening question."""
    history = [{"role": "system", "content": build_system_prompt(job_title, jd_text, questions)}]

    raw_text = await chat_completion(
        history,
        model=settings.interview_llm_model,
        exclude_reasoning=True,
        fallback_model=settings.interview_llm_fallback_model,
    )
    ai_text, is_complete = strip_completion_sentinel(raw_text)
    history.append({"role": "assistant", "content": ai_text})

    ai_audio = await synthesize(ai_text)
    return InterviewTurnResult(
        transcript=None, ai_text=ai_text, ai_audio=ai_audio, is_complete=is_complete, history=history
    )


async def run_turn(history: list[dict], candidate_audio: bytes, audio_format: str = "wav") -> InterviewTurnResult:
    """One turn: candidate's spoken answer in, interviewer's next spoken line out. Callers
    should pass an already-bound `history` (see bound_history) — this function does not bound
    it itself, per ADR-007's requirement that its signature not change for M4."""
    transcript = await transcribe(candidate_audio, audio_format=audio_format)

    history = [*history, {"role": "user", "content": transcript}]
    raw_text = await chat_completion(
        history,
        model=settings.interview_llm_model,
        exclude_reasoning=True,
        fallback_model=settings.interview_llm_fallback_model,
    )
    ai_text, is_complete = strip_completion_sentinel(raw_text)
    history = [*history, {"role": "assistant", "content": ai_text}]

    ai_audio = await synthesize(ai_text)
    return InterviewTurnResult(
        transcript=transcript, ai_text=ai_text, ai_audio=ai_audio, is_complete=is_complete, history=history
    )
