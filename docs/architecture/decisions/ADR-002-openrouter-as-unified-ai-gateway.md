# ADR-002: OpenRouter as the unified gateway for LLM, STT, and TTS

- Status: Accepted
- Date: 2026-08-05
- Owners: Amit Tiwari
- Related product decision: PD-001 (async audio interview before live/video), PD-002 (cost-sensitive POC scope)
- Supersedes: none
- Superseded by: none

## Context
The platform needs three categories of AI capability: text LLM calls (resume structuring,
interview question generation, answer evaluation), speech-to-text (transcribing candidate
answers), and text-to-speech (the AI interviewer's spoken output). Amit chose to route all
three through OpenRouter rather than calling each provider's API directly, using specific
models: `nvidia/nemotron-3-ultra-550b-a55b:free` (interview LLM), `qwen/qwen3-asr-flash-...`
(STT), `hexgrad/kokoro-82m` (TTS), with `openai/gpt-4o-mini` for resume structuring.

## Decision drivers
- Cost-sensitive POC — needed cheap/free models with the option to swap without rewriting code.
- Wanted one API key and one client pattern for all AI calls rather than N provider SDKs.
- Needed to validate the STT/LLM/TTS request formats empirically (OpenRouter's audio API docs
  were incomplete/ambiguous when checked), so being able to test cheaply and iterate mattered.

## Considered options

### Option 1: OpenRouter for everything (LLM, STT, TTS)
One key, one OpenAI-compatible base URL pattern, per-call model slug. Confirmed to support all
three modalities as of this session (`/chat/completions`, `/audio/transcriptions`,
`/audio/speech`).

### Option 2: Direct provider APIs per capability
E.g. Anthropic/OpenAI direct for LLM, a dedicated STT provider, a dedicated TTS provider.
More control per provider, but N credentials, N client implementations, and no single place to
swap a model.

### Option 3: Self-hosted models (e.g. local Whisper for STT)
Considered and originally planned for STT (see the project's early milestone roadmap) before
this decision. Rejected once Qwen3 ASR Flash on OpenRouter turned out to be extremely cheap
(~$0.000035/sec of audio) and required no GPU/CPU inference infrastructure to manage.

## Decision
Use OpenRouter for all three AI capabilities (Option 1).

## Rationale
A single gateway meant the `services/llm_client.py` pattern (model name read from config) could
be replicated almost identically for `stt_client.py` and `tts_client.py`, keeping every AI call
swappable per task via `.env`/`app/config.py` without touching calling code. It also removed the
need to stand up and maintain self-hosted inference (originally planned for STT).

## Consequences

### Positive
- One credential, one client pattern, model choice is a config change everywhere.
- Confirmed empirically this session: STT, LLM, and TTS all worked end-to-end through
  OpenRouter with real audio round-trips (see `scripts/test_interview_pipeline.py`).
- No self-hosted inference infrastructure (GPU/CPU capacity planning) needed for the POC.

### Negative
- Full vendor dependence on OpenRouter's uptime/pricing/model availability for every AI call in
  the system — a single point of failure for the entire AI layer.
- OpenRouter's own docs were incomplete on the exact audio request/response shape; correct
  behavior was confirmed only by making real calls and reading actual responses/errors, not
  from documentation alone.

### Risks
- The free-tier interview LLM (`nvidia/nemotron-3-ultra-550b-a55b:free`) may have undocumented
  rate limits or be discontinued; no fallback is wired up yet (paid alternatives — DeepSeek V4
  Pro, GLM-5.2 — were identified but not implemented as automatic fallback).
- Reasoning models on OpenRouter can leak internal "thinking" into visible output unless
  `reasoning.exclude` is explicitly set — confirmed as a real failure mode this session (fixed
  in `llm_client.py`), and is a class of bug that could recur with a different reasoning model.

## Validation plan
None formal beyond this session's manual smoke test (`scripts/test_interview_pipeline.py`) —
transcript round-trip accuracy and multi-turn conversational coherence were checked by eye, not
against a defined accuracy threshold.

## Migration and rollout
N/A — adopted directly, no prior gateway to migrate from.

## Rollback or exit strategy
Each client (`llm_client.py`, `stt_client.py`, `tts_client.py`) is a thin, isolated wrapper —
replacing OpenRouter with direct provider APIs would mean rewriting these three files, not the
callers. No app code outside `app/services/` knows OpenRouter exists.

## Revisit triggers
- OpenRouter pricing/availability changes materially for the models in use.
- Free-tier LLM proves unreliable at real interview volume (untested — current validation is a
  two-turn scripted smoke test, not production load).
- Latency becomes unacceptable for a live/real-time interview mode (M7) — cascaded STT→LLM→TTS
  round-trip latency has not been measured end-to-end yet.

## Unresolved questions
- No automatic fallback if the primary interview LLM is rate-limited or unavailable — is that
  needed before M4 (wiring the cascade into the real app), or can it wait?
- No cost tracking wired up yet (`ai_processing_logs` table exists in the schema but nothing
  writes to it) — actual per-interview cost is currently unmeasured, only estimated from
  published per-token/per-second pricing.
