"""Cascaded voice interview pipeline: STT -> LLM -> TTS.

This is the "brain" of the async audio interview: given a running
conversation history and the candidate's latest spoken answer, it transcribes
the answer, asks the interviewer LLM what to say next, and synthesizes that
reply back to audio. History is a plain list of chat messages (system/user/
assistant) — the LLM is the only thing that needs to "remember" the
conversation, so that list *is* the session state.
"""

from dataclasses import dataclass, field

from app.config import settings
from app.services.llm_client import chat_completion
from app.services.stt_client import transcribe
from app.services.tts_client import synthesize

SYSTEM_PROMPT_TEMPLATE = """You are an AI interviewer conducting a first-round screening interview for the \
following role. Ask one question at a time, keep questions concise (2-3 sentences max, spoken aloud), and ask \
natural follow-ups based on what the candidate actually says. Do not repeat a question you've already asked.

Job title: {job_title}
Job description: {jd_text}

Start the interview now with your opening question. Respond with ONLY the question text — no preamble, no \
labels like "Question 1:", just what you would say out loud.
"""


@dataclass
class InterviewTurnResult:
    transcript: str | None  # candidate's transcribed answer; None for the opening turn
    ai_text: str
    ai_audio: bytes
    history: list[dict] = field(default_factory=list)


async def start_interview(job_title: str, jd_text: str) -> InterviewTurnResult:
    """Seed a new interview: build the system prompt and get the opening question."""
    history = [{"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(job_title=job_title, jd_text=jd_text)}]

    ai_text = await chat_completion(history, model=settings.interview_llm_model, exclude_reasoning=True)
    history.append({"role": "assistant", "content": ai_text})

    ai_audio = await synthesize(ai_text)
    return InterviewTurnResult(transcript=None, ai_text=ai_text, ai_audio=ai_audio, history=history)


async def run_turn(history: list[dict], candidate_audio: bytes, audio_format: str = "wav") -> InterviewTurnResult:
    """One turn: candidate's spoken answer in, interviewer's next spoken line out."""
    transcript = await transcribe(candidate_audio, audio_format=audio_format)

    history = [*history, {"role": "user", "content": transcript}]
    ai_text = await chat_completion(history, model=settings.interview_llm_model, exclude_reasoning=True)
    history = [*history, {"role": "assistant", "content": ai_text}]

    ai_audio = await synthesize(ai_text)
    return InterviewTurnResult(transcript=transcript, ai_text=ai_text, ai_audio=ai_audio, history=history)
