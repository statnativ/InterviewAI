"""Standalone smoke test for the STT -> LLM -> TTS interview cascade.

Validates all three legs and multi-turn memory without needing a real
microphone: we *synthesize* fake candidate answers with the TTS model, feed
them back through STT (a clean round-trip check), then let the interviewer
LLM react across two turns to prove conversation history actually carries
context forward.

IA-002 timing instrumentation: wraps transcribe/chat_completion/synthesize at
their app.services.interview_pipeline import site to record per-leg duration
without touching interview_pipeline.py itself (it stays a clean business-logic
module, no timing side effects baked in). Prints a per-turn breakdown plus a
summary against ADR-007's ~25-30s realistic-client-timeout threshold at the
end. n=2 turns from one run — enough for a first real number, not enough for
a genuine p95; said explicitly in the output rather than overstated.

Run from the project root:
    source venv/bin/activate
    python scripts/test_interview_pipeline.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.services.interview_pipeline as interview_pipeline  # noqa: E402
from app.services.interview_pipeline import run_turn, start_interview  # noqa: E402
from app.services.tts_client import synthesize  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "pipeline_test"

TIMINGS: list[dict] = []  # [{"turn": 0, "leg": "llm", "seconds": 1.23}, ...]
_current_turn = {"n": 0}


def _timed(fn, leg: str):
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        TIMINGS.append({"turn": _current_turn["n"], "leg": leg, "seconds": elapsed})
        return result

    return wrapper


# Patch the names interview_pipeline.py actually calls (bound at its own
# module namespace via `from ... import ...`), not the origin modules.
interview_pipeline.transcribe = _timed(interview_pipeline.transcribe, "stt")
interview_pipeline.chat_completion = _timed(interview_pipeline.chat_completion, "llm")
interview_pipeline.synthesize = _timed(interview_pipeline.synthesize, "tts")

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
    _current_turn["n"] = 0  # opening turn: LLM + TTS only, no candidate audio yet
    opening_start = time.perf_counter()
    turn = await start_interview(JOB_TITLE, JD_TEXT)
    opening_total = time.perf_counter() - opening_start
    (OUT_DIR / "00_opening_question.mp3").write_bytes(turn.ai_audio)
    print(f"[AI opening question] {turn.ai_text}")
    print(f"  saved audio -> {OUT_DIR / '00_opening_question.mp3'}")
    print(f"  [timing] opening turn total: {opening_total:.2f}s")

    history = turn.history

    for i, fake_answer in enumerate(FAKE_ANSWERS, start=1):
        print(f"\n--- Turn {i}: synthesizing fake candidate answer ---")
        candidate_audio = await synthesize(fake_answer, voice="am_adam")
        candidate_path = OUT_DIR / f"{i:02d}a_candidate_answer.mp3"
        candidate_path.write_bytes(candidate_audio)
        print(f"  candidate said (ground truth): {fake_answer}")
        print(f"  saved audio -> {candidate_path}")

        _current_turn["n"] = i
        turn_start = time.perf_counter()
        result = await run_turn(history, candidate_audio, audio_format="mp3")
        turn_total = time.perf_counter() - turn_start
        history = result.history

        print(f"  [STT transcript]     {result.transcript}")
        print(f"  [AI next question]   {result.ai_text}")
        print(f"  [timing] turn {i} total (STT+LLM+TTS): {turn_total:.2f}s")

        ai_path = OUT_DIR / f"{i:02d}b_ai_response.mp3"
        ai_path.write_bytes(result.ai_audio)
        print(f"  saved audio -> {ai_path}")

    print("\n--- Done. Full conversation history: ---")
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        print(f"  {role:9s}: {content[:120]}")

    _print_timing_summary()


def _print_timing_summary():
    print("\n--- IA-002 timing summary (per-leg, seconds) ---")
    print(f"{'turn':>4}  {'leg':>4}  {'seconds':>8}")
    for row in TIMINGS:
        print(f"{row['turn']:>4}  {row['leg']:>4}  {row['seconds']:>8.2f}")

    real_turns = [t for t in {r["turn"] for r in TIMINGS} if t > 0]  # exclude opening (no STT leg)
    turn_totals = {t: sum(r["seconds"] for r in TIMINGS if r["turn"] == t) for t in real_turns}
    leg_totals: dict[str, list[float]] = {}
    for r in TIMINGS:
        if r["turn"] in real_turns:
            leg_totals.setdefault(r["leg"], []).append(r["seconds"])

    print(f"\nFull-turn (STT+LLM+TTS) totals, n={len(turn_totals)}:")
    for t, total in turn_totals.items():
        print(f"  turn {t}: {total:.2f}s")
    if turn_totals:
        values = sorted(turn_totals.values())
        print(f"  min={values[0]:.2f}s  max={values[-1]:.2f}s")
        print(
            "  (n too small for a real p50/p95 — this is a first grounded data point, "
            "not a statistically meaningful percentile; re-run with more turns before "
            "treating this as final)"
        )

    print("\nPer-leg average across turns:")
    for leg, values in leg_totals.items():
        print(f"  {leg}: avg={sum(values) / len(values):.2f}s  values={[f'{v:.2f}' for v in values]}")

    threshold = 27.5  # midpoint of ADR-007's ~25-30s realistic client/proxy timeout ceiling
    over = [t for t, total in turn_totals.items() if total > threshold]
    if over:
        print(
            f"\n[ADR-007] {len(over)}/{len(turn_totals)} turn(s) exceeded the ~{threshold:.0f}s "
            "threshold — Option 4 (wait for the full response) may not be viable as-is; "
            "see ADR-007's Validation plan step 4."
        )
    else:
        print(
            f"\n[ADR-007] All turns under the ~{threshold:.0f}s threshold — Option 4 confirmed "
            "viable for the asynchronous mode on this sample."
        )


if __name__ == "__main__":
    asyncio.run(main())
