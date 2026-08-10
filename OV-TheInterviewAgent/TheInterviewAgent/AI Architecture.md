---
tags: [project, system-design, ai, openrouter]
status: current — gateway + deterministic screening + question generation + LLM-as-judge
  scoring live; retry/fallback built (IA-009); the voice cascade's app wiring (M4) not started
last-updated: 2026-08-10
---

# The Interview Agent — AI Architecture

How the AI works: the single gateway, which models are used for which task, each AI service
in detail, and — just as important — **what is deliberately not AI**. Companion to
[[Backend Overview]]; the decision records behind this are ADR-002 (OpenRouter as the AI
gateway), ADR-004 (cascaded voice pipeline), and **ADR-007** (execution model for live
interview turns, M4) in `docs/architecture/decisions/`.

## The core principle: one gateway, per-task models

Every AI call — LLM, speech-to-text, text-to-speech — goes through **OpenRouter** with one
API key (`OPENROUTER_API_KEY` in `.env`), via **one shared, connection-pooled `httpx.AsyncClient`**
(`llm_client.get_http_client()`, added 2026-08-10/IA-014 — each call used to open its own
client, meaning a fresh TCP/TLS handshake per call; now the cascade's three legs reuse one
connection). OpenRouter bills the account and routes to whichever model slug is specified per
call. Consequences:

- No per-vendor SDKs or keys; adding a model is a config change, not a code change.
- Model choice is **config-driven per task** (the slug lives in `app/config.py` settings).
- **Resilience exists now, but only for hard failures.** `interview_llm_model` (the one
  genuinely free-tier model here) automatically falls back to `interview_llm_fallback_model`
  (`deepseek/deepseek-v4-pro`) on timeout, network error, non-200, or a malformed response —
  built 2026-08-10 (IA-009) after IA-002's latency measurement reproduced both a real 60s
  timeout and a malformed response live, not just in theory. STT/TTS get one same-model retry
  with backoff — no second model is on record for either, so a swap isn't the honest fix there.
  **What this doesn't cover**: a call that's slow but technically succeeds — the same
  verification run that confirmed this wiring also hit a real 24.63s single LLM call that
  returned fine; the fallback correctly leaves that alone, since a performance guarantee would
  need racing against a shorter timeout, a different and bigger design not built here.
  (`llm_client.get_http_client`/`post_with_retry`; `app/config.py`'s `interview_llm_fallback_model`.)

## Model choices in use (cost-sensitive POC)

| Task | Model | Slug | Cost |
|---|---|---|---|
| LLM — interview brain | Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b:free` | free tier |
| LLM — interview brain fallback | DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | $0.435 / $0.87 per M tok — **wired and used automatically** on primary failure (IA-009), not just a documented manual option anymore |
| LLM — resume/question structuring/candidate judging | GPT-4o mini | `openai/gpt-4o-mini` | cheap default — no fallback wired (not free-tier, hasn't shown the reliability issues Nemotron has). Three call sites now: `resume_parser.py` (dormant, off the ATS path), `question_generator.py` (M3), `candidate_judge.py` (M2, LLM-as-judge — new) |
| STT | Qwen3 ASR Flash | `qwen/qwen3-asr-flash-2026-02-10` | $0.000035/sec (~$0.13/hr audio) — one same-model retry, no fallback model |
| TTS | Kokoro 82M | `hexgrad/kokoro-82m` | $0.62/M characters — **paid, not free-tier** (corrected 2026-08-10; an earlier note here mistakenly called it free-tier); one same-model retry, no fallback model |
| LLM — manual-only contingency | GLM-5.2 | `z-ai/glm-5.2` | $0.406 / $1.276 per M tok — documented fallback-of-the-fallback, not wired into any automatic path |

Rationale for the free-tier brain + cheap STT/TTS pair: see
`docs/product-decisions/PD-002-cost-sensitive-poc-scope.md`.

## The AI services, one by one
### `llm_client.py` — the text gateway
OpenRouter `/chat/completions`. Every text-in/text-out call (resume structuring, interview
questions) goes through this. Supports `exclude_reasoning=True` — reasoning models
(Nemotron) sometimes put their internal "thinking" in `message.content`, which is fine for
text but unacceptable for something read aloud to a candidate; this strips it.

**Resolved 2026-08-10 (was an open gap since this project's first architecture review):** the
response used to be indexed without validation, so a malformed 200 could raise an uncaught
`KeyError`. This wasn't theoretical — IA-002's latency measurement reproduced it live against
the real free-tier model. `chat_completion` now validates the response shape and raises a clean
`LLMError`, and a raw `httpx.TimeoutException`/`TransportError` (which used to propagate
completely uncaught — the exact thing that crashed IA-002's very first run, a 60s TTS timeout
with no error at all) is now caught and wrapped too. That wrapping is what makes the retry/
fallback logic (`post_with_retry`, above) reachable at all — a failure has to be an `LLMError`
for anything to retry on it.

`chat_completion` also takes an opt-in `fallback_model` — only `interview_pipeline.py` passes
one; résumé parsing and question generation are unaffected and keep their original
single-attempt behavior against their own (paid) models.

### `stt_client.py` — speech-to-text
OpenRouter `/audio/transcriptions`: audio bytes in, transcript text out. The cheapest
reliable ASR found for the POC ($0.13/hour of audio). One same-model retry with backoff on
timeout/network/non-200 failure (IA-009) — no observed failures here yet, added for
consistency with the other two cascade legs, which both did fail live during IA-002.

### `tts_client.py` — text-to-speech
OpenRouter `/audio/speech`: text in, mp3 bytes out. Kokoro 82M — small, cheap, fast, and
**paid** (not free-tier). One same-model retry with backoff (IA-009) — this is the leg that
actually hit a full 60s timeout during IA-002's measurement.

### `interview_pipeline.py` — the cascade (STT → LLM → TTS)
Chains the three above. `start_interview()` seeds the conversation + gets the opening
question; `run_turn()` does transcribe → ask LLM → synthesize, one candidate turn at a time —
both pass `fallback_model=settings.interview_llm_fallback_model` to the LLM leg.
**Conversation history (a plain list of chat messages) *is* the session state** — `run_turn`
takes it in and returns the updated list, holding no state itself; this is exactly what makes
ADR-007's "externalize state to Postgres" requirement for M4 a caller-side addition, not a
rewrite of this module. Currently a standalone demo
(`scripts/test_interview_pipeline.py`) — real, live-verified, and now instrumented with per-leg
timing (IA-002) — but still not wired into the app (that's M4; see ADR-007 for the execution
model chosen for it).

**IA-002's real numbers** (2026-08-10, `scripts/test_interview_pipeline.py`, n=2 clean turns —
not a real p50/p95, a first grounded data point): full-turn (STT+LLM+TTS) totals 8.24s and
12.51s, comfortably under ADR-007's ~25–30s viability ceiling. Per-leg: STT ~1s, **TTS is the
dominant leg at 4.9–5.9s, not the LLM** (2.4–5.5s on the clean run, though one separate run saw
a single LLM call take 24.63s — real variance, not a one-time fluke). Worth knowing before any
future optimization effort targets the wrong service.

### What is deliberately NOT AI

- **Screening / scoring** (`services/screening.py`) — deterministic keyword matching against
  the 163-skill dictionary: rubric generation, `derive_score`, strengths/gaps. No LLM on the
  request path (fast, free, reproducible). The "LLM-as-judge" upgrade is M2's open question.
- **PDF text extraction** — happens in the browser (pdfjs) for uploads, or via
  `resume_parser.extract_text` server-side. No AI.
- **Schema/seed data** — the synthetic corpus was LLM-generated *offline* (once, by the
  synthetic-data pipeline), but the app itself never calls an LLM for it.

## Costs & operational notes

- Every AI call is billed through the single OpenRouter key; the audit trail table
  (`ai_processing_logs`) exists but is **not yet written to** — per-call token/cost logging
  is future work (IA-001, still not started).
- Retry/fallback exists now for the interview cascade specifically (above) — a broader
  OpenRouter-as-single-gateway outage (R-003) is still entirely unmitigated, since the fallback
  model is also routed through OpenRouter.

## PII & the account

- Credentials live in `.env` (never committed): `DATABASE_URL` and `OPENROUTER_API_KEY`
  (generated at openrouter.ai/keys). `.env.example` is the committed blank template.
- Resumes contain PII and are saved to disk **before** any downstream processing; a failed
  processing step can still orphan a file with no DB row and no cleanup — unresolved. Interview
  audio (once M4 persists it) inherits the identical gap — flagged explicitly as a hard
  dependency for M4's build in ADR-007, not deferrable past it.

## Where AI is still fake or missing (gaps)

| Area                                   | Status                                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Screening                              | ✅ deterministic & live (free default); ✅ LLM-as-judge also live (M2, 2026-08-10) — explicit, additive, reasons over full candidate profile not just keyword presence; ❌ execution still inline, not moved off the request path (IA-003) |
| Rubric generation from JD              | ✅ live (deterministic, `generate_rubric`)                                                              |
| Question generation                    | ✅ live (M3) — LLM-drafted from the JD, optional per-candidate personalization, edit/reorder/regenerate |
| AI-call resilience (interview cascade) | ✅ live (IA-009) — retry + fallback on hard failures; ❌ no protection against slow-but-successful calls |
| Voice cascade in the app               | ❌ standalone script only, though real, live-verified, and timed (IA-002) — M4 wires it in; see ADR-007 |
| Answer evaluation + report             | ❌ (M5)                                                                                                 |
| Frontend voice/video sessions          | ❌ recording is simulated; avatar is a static icon (see [[Frontend Overview]])                          |
