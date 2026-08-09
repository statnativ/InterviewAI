"""Standalone smoke test for the STT -> LLM -> TTS interview cascade.

Validates all three legs and multi-turn memory without needing a real
microphone: we *synthesize* fake candidate answers with the TTS model, feed
them back through STT (a clean round-trip check), then let the interviewer
LLM react across two turns to prove conversation history actually carries
context forward.

Run from the project root:
    source venv/bin/activate
    python scripts/test_interview_pipeline.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.interview_pipeline import run_turn, start_interview  # noqa: E402
from app.services.tts_client import synthesize  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "pipeline_test"

JOB_TITLE = "Staff AI Architect"
JD_TEXT = (
    "We need a staff AI architect with deep LLM orchestration and distributed systems experience "
    "to lead our AI platform team and design our next-generation ML infrastructure."
)

# Fake candidate answers, spoken via TTS so we have real audio to transcribe.
# The second answer deliberately references the first, so we can check the
# LLM's second question actually engages with earlier context.
FAKE_ANSWERS = [
    "Sure, I led the redesign of our recommendation platform at my last company, moving it from a "
    "monolithic batch pipeline to a real time event driven architecture using Kafka and a feature store. "
    "That cut our model refresh latency from twenty four hours to under five minutes.",
    "The biggest challenge was actually organizational, not technical. We had three teams independently "
    "building similar feature pipelines, so I introduced a shared feature store contract and ran a series "
    "of design reviews to get everyone aligned before we touched any code.",
]


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"--- Starting interview for: {JOB_TITLE} ---")
    turn = await start_interview(JOB_TITLE, JD_TEXT)
    (OUT_DIR / "00_opening_question.mp3").write_bytes(turn.ai_audio)
    print(f"[AI opening question] {turn.ai_text}")
    print(f"  saved audio -> {OUT_DIR / '00_opening_question.mp3'}")

    history = turn.history

    for i, fake_answer in enumerate(FAKE_ANSWERS, start=1):
        print(f"\n--- Turn {i}: synthesizing fake candidate answer ---")
        candidate_audio = await synthesize(fake_answer, voice="am_adam")
        candidate_path = OUT_DIR / f"{i:02d}a_candidate_answer.mp3"
        candidate_path.write_bytes(candidate_audio)
        print(f"  candidate said (ground truth): {fake_answer}")
        print(f"  saved audio -> {candidate_path}")

        result = await run_turn(history, candidate_audio, audio_format="mp3")
        history = result.history

        print(f"  [STT transcript]     {result.transcript}")
        print(f"  [AI next question]   {result.ai_text}")

        ai_path = OUT_DIR / f"{i:02d}b_ai_response.mp3"
        ai_path.write_bytes(result.ai_audio)
        print(f"  saved audio -> {ai_path}")

    print("\n--- Done. Full conversation history: ---")
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        print(f"  {role:9s}: {content[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
