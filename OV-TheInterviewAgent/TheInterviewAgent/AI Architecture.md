---
tags: [project, system-design, ai, openrouter]
status: current — gateway + deterministic screening live; LLM-as-judge not started
last-updated: 2026-08-09
---

# The Interview Agent — AI Architecture

How the AI works: the single gateway, which models are used for which task, each AI service
in detail, and — just as important — **what is deliberately not AI**. Companion to
[[Backend Overview]]; the decision records behind this are ADR-002 (OpenRouter as the AI
gateway) and ADR-004 (cascaded voice pipeline) in `docs/architecture/decisions/`.

## The core principle: one gateway, per-task models

Every AI call — LLM, speech-to-text, text-to-speech — goes through **OpenRouter** with one
API key (`OPENROUTER_API_KEY` in `.env`). OpenRouter bills the account and routes to whichever
model slug is specified per call. Consequences:

- No per-vendor SDKs or keys; adding a model is a config change, not a code change.
- Model choice is **config-driven per task** (the slug lives in `app/config.py` settings).
- One failure mode to watch: if OpenRouter (or the chosen model) is unavailable, there is no
  fallback yet (tracked in the risk register).

## Model choices in use (cost-sensitive POC)

| Task | Model | Slug | Cost |
|---|---|---|---|
| LLM — interview brain | Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b:free` | free tier |
| LLM — resume structuring | GPT-4o mini | `openai/gpt-4o-mini` | cheap default |
| STT | Qwen3 ASR Flash | `qwen/qwen3-asr-flash-2026-02-10` | $0.000035/sec (~$0.13/hr audio) |
| TTS | Kokoro 82M | `hexgrad/kokoro-82m` | $0.62/M characters |
| LLM — paid fallbacks (unused) | DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | $0.435 / $0.87 per M tok |
| LLM — paid fallbacks (unused) | GLM-5.2 | `z-ai/glm-5.2` | $0.406 / $1.276 per M tok |

Rationale for the free-tier brain + cheap STT/TTS pair: see
`docs/product-decisions/PD-002-cost-sensitive-poc-scope.md`.

## The AI services, one by one

### `llm_client.py` — the text gateway
OpenRouter `/chat/completions`. Every text-in/text-out call (resume structuring, interview
questions) goes through this. Supports `exclude_reasoning=True` — reasoning models
(Nemotron) sometimes put their internal "thinking" in `message.content`, which is fine for
text but unacceptable for something read aloud to a candidate; this strips it.
⚠️ Known gap (from the architecture review): the response is indexed without validation, so
a timeout/malformed response can raise an uncaught exception → 500 instead of a clean error.

### `stt_client.py` — speech-to-text
OpenRouter `/audio/transcriptions`: audio bytes in, transcript text out. The cheapest
reliable ASR found for the POC ($0.13/hour of audio).

### `tts_client.py` — text-to-speech
OpenRouter `/audio/speech`: text in, mp3 bytes out. Kokoro 82M — small, cheap, fast.

### `interview_pipeline.py` — the cascade (STT → LLM → TTS)
Chains the three above. `start_interview()` seeds the conversation + gets the opening
question; `run_turn()` does transcribe → ask LLM → synthesize, one candidate turn at a time.
**Conversation history (a plain list of chat messages) *is* the session state** — no separate
state store needed at this scale. Currently a standalone demo
(`scripts/test_interview_pipeline.py`), not wired into the app (that's M4).

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
  is future work (M5 territory).
- No fallback models and no retry logic yet — a gateway outage means the voice cascade fails.

## PII & the account

- Credentials live in `.env` (never committed): `DATABASE_URL` and `OPENROUTER_API_KEY`
  (generated at openrouter.ai/keys). `.env.example` is the committed blank template.
- Resumes contain PII and are saved to disk **before** any downstream processing; the
  architecture review flagged that a failed processing step can orphan a file with no DB row
  and no cleanup (still open — D1).

## Where AI is still fake or missing (gaps)

| Area | Status |
|---|---|
| Screening | ✅ deterministic & live; ❌ LLM-as-judge not started (M2) |
| Rubric generation from JD | ✅ live (deterministic, `generate_rubric`) |
| Question generation | ❌ interviews get seeded questions only (M3) |
| Voice cascade in the app | ❌ standalone script only (M4: wire it + DB persistence) |
| Answer evaluation + report | ❌ (M5) |
| Frontend voice/video sessions | ❌ recording is simulated; avatar is a static icon (see [[Frontend Overview]]) |
