---
tags: [project, system-design, ai, openrouter]
status: current — gateway + deterministic screening + question generation + LLM-as-judge
  scoring live, off the request path (IA-003); retry/fallback built (IA-009); the voice/video
  cascade is wired into the app (M4/M4b); interview evaluation (M5) runs the same LLM-as-judge
  shape off-request via Celery+Redis, not BackgroundTasks — see ADR-009
last-updated: 2026-08-11
---

# The Interview Agent — AI Architecture

How the AI works: the single gateway, which models are used for which task, each AI service
in detail, and — just as important — **what is deliberately not AI**. Companion to
[[Backend Overview]]; the decision records behind this are ADR-002 (OpenRouter as the AI
gateway), ADR-004 (cascaded voice pipeline), ADR-007 (execution model for live interview
turns, M4), ADR-008 (candidate session auth + audio storage, M4), and **ADR-009** (Celery+Redis
execution model for interview evaluation, M5) in `docs/architecture/decisions/`.

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
| LLM — resume/question structuring/candidate + interview judging | GPT-4o mini | `openai/gpt-4o-mini` | cheap default — no fallback wired (not free-tier, hasn't shown the reliability issues Nemotron has). Four call sites now: `resume_parser.py` (dormant, off the ATS path), `question_generator.py` (M3), `candidate_judge.py` (M2, LLM-as-judge), `interview_evaluator.py` (M5, LLM-as-judge over a transcript instead of a résumé profile — new) |
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

**Pre-implementation architecture review, 2026-08-10 (`/architect-review`, before any M4 code
exists)** — ADR-007 is thorough on *transport* (which of `BackgroundTasks`/Celery/WebSocket/
sync fits M4's live-turn shape) but was reviewed in isolation from one question it never asks:
**who is actually calling the new endpoint.** Confirmed by direct inspection of `app/deps.py`
and `app/services/authz.py`: only three roles exist (`admin`/`recruiter`/`hiring_manager`), all
resolved via the recruiter-side `X-Tenant-Id`/`X-User-Email` dev headers. **No candidate identity
or auth mechanism exists anywhere in the codebase.** The moment M4's turn endpoint goes live, it
would be the first candidate-facing route persisting real conversational PII (more sensitive than
a résumé, per R-006's own framing) with nothing in front of it — R-001's "no auth exists, don't
expose beyond localhost" posture would be silently inherited by a brand-new persisted-transcript
table, not just the existing recruiter-side routes it was written about.

Two lower-severity findings from the same review: `docs/implementation-actions.md`'s **IA-006**
(the tracked M4 action) lists `Dependencies: IA-002, IA-004` but omits **IA-008** (PII/
encryption) — even though ADR-007's own "Unresolved questions" section calls audio storage "not
deferrable past M4's build." A real contradiction between two of the project's own decision
artifacts, cheap to fix, easy to miss once implementation is moving. And: no automated test file
exists for `interview_pipeline.py` (only the manual `scripts/test_interview_pipeline.py`),
unlike M2/M3 which both shipped a monkeypatched-`chat_completion` pytest suite alongside the
router work, not after it.

**Verdict: proceed with conditions** — ADR-007's core transport decision doesn't need
revisiting, but the candidate-auth question (even a minimal answer — e.g., the unguessable
`interview_sessions.id` itself as a bearer token, consistent with this project's POC-stage
posture elsewhere) needs an explicit decision before the turn endpoint's contract is built, not
after.

**Resolved before the build, not discovered after (ADR-008, same day):** `interview_sessions.id`
adopted as the bearer credential exactly as this review recommended; audio storage shipped as
raw/unencrypted, deliberately risk-accepted rather than solved (widens R-006, doesn't close it);
IA-006's dependency list issue and the missing test file were both fixed directly — 12 new tests
now exist (`tests/test_interview_sessions.py`). A second design-validation pass, run the same
day before any router code was written, caught one more structural gap this review missed: the
cascade's original open-ended system prompt had no termination signal at all, while
`VoiceInterviewSession.tsx` was already built entirely around a fixed `questions[step]` list —
fixed by having the interviewer ask the interview's own M3-curated questions in order, ending
with a detectable sentinel. See [[Project Overview]]'s M4 section for the full build writeup.

### `interview_evaluator.py` — scoring a completed interview (M5)

The fifth `chat_completion` call site, and the second LLM-as-judge shape after
`candidate_judge.py` (same prompt structure, same never-trust-the-response coercion — the
shared clamp/scorecard logic lives in `llm_scoring.py` so it isn't duplicated). The only real
difference from `candidate_judge.py`: the input is a completed interview's full transcript
(built by walking `interview_turns` in order), not a candidate's structured résumé profile, and
the rubric it's scored against is still `Job.rubric` — whole-interview evaluation, not a new
per-question rubric concept.

**Runs off the request path, but not via `BackgroundTasks`** — this is the codebase's first
Celery+Redis call, triggered automatically the moment an `interview_sessions` row flips to
`status="complete"`. ADR-007 (written during M4 planning) had already earmarked this exact
workload as the "genuinely delay-tolerant batch work" that would finally justify a real task
queue instead of reusing `BackgroundTasks` a third time. Full reasoning — including the real
gotcha (Celery workers and this codebase's lazy async singletons, `app.db`'s engine and
`llm_client.get_http_client()`'s shared client, don't mix safely without a persistent
per-worker-process event loop) — in **ADR-009**.

Live-verified end-to-end against the real API and a real worker: a genuine transcript ("led the
redesign of our recommendation platform... Kafka and a feature store") scored 60/100 overall,
0/100 on a Python criterion the candidate never mentioned, correctly distinct from a stronger
Distributed-Systems score — reasoned output, not a placeholder.

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
  audio (M4 now persists it — `data/interview_audio/{session_id}/`, unencrypted, same
  `save_upload`-style pattern) inherits the identical gap. ADR-007 flagged this as a hard,
  non-deferrable dependency for M4's build; ADR-008 records the decision to ship it plainly and
  accept the risk (widening R-006's scope, deliberately, not silently) rather than solve
  encryption inside that milestone.

## Where AI is still fake or missing (gaps)

| Area                                   | Status                                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Screening                              | ✅ deterministic & live (free default); ✅ LLM-as-judge also live (M2, 2026-08-10) — explicit, additive, reasons over full candidate profile not just keyword presence; ✅ execution moved off the request path (IA-003, 2026-08-10) — `POST /candidates/{id}/judge` returns `202` via `BackgroundTasks`, frontend polls `GET /candidates/{id}`; this codebase's first `BackgroundTasks` usage |
| Rubric generation from JD              | ✅ live (deterministic, `generate_rubric`)                                                              |
| Question generation                    | ✅ live (M3) — LLM-drafted from the JD, optional per-candidate personalization, edit/reorder/regenerate |
| AI-call resilience (interview cascade) | ✅ live (IA-009) — retry + fallback on hard failures; ❌ no protection against slow-but-successful calls |
| Voice/video cascade in the app         | ✅ live (M4/M4b) — Voice and Video modes; real session creation + turn endpoint, curated-question-driven with a detectable end-of-interview signal; live-verified against the real API, including a real TTS-timeout failure hitting the designed retry path; see ADR-007/ADR-008 |
| Answer evaluation + report             | ✅ live (M5, 2026-08-11) — a completed transcript is scored against the job's rubric off-request via Celery+Redis, with a real per-criterion scorecard, strengths/gaps, and verdict; recruiter-facing report page with real playback and a human-override decision; see ADR-009 |
| Frontend voice/video sessions          | ✅ Voice and Video mode real (M4/M4b) — `MediaRecorder` capture, real AI audio playback; ❌ Chat mode still simulated, avatar is still a static icon (see [[Frontend Overview]])                          |
