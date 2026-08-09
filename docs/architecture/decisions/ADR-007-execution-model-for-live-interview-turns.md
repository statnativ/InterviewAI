# ADR-007: Execution model for live AI interview turns (M4)

- Status: Proposed
- Date: 2026-08-10 (revised same day — second pass, evidence from direct reads of
  `interview_pipeline.py`/`stt_client.py`/`tts_client.py`, run via the `engineering:architecture`
  skill against the first pass's conclusion)
- Owners: Amit Tiwari
- Related product decision: PD-001 (async audio before live video)
- Supersedes: none
- Superseded by: none

## Context

M4 ("wire the voice cascade into the app + persistence") is the next unstarted milestone.
Today, `app/services/interview_pipeline.py` proves STT→LLM→TTS works end-to-end only via a
standalone script (`scripts/test_interview_pipeline.py`) — no HTTP endpoint, no persistence, no
candidate-reachable path exists. `Project Overview.md`'s roadmap frames the concept M4 teaches
as *"background workers — why BackgroundTasks stops being enough → Celery+Redis"*, and the risk
register already flags two related gaps: every AI call in the app runs inline on the request
thread with no background execution introduced anywhere yet (confirmed — no celery/redis/rq/arq
appears in `requirements.txt`), and `interview_pipeline.py`'s conversation history is an
unbounded in-memory Python list (R-010).

`run_turn()` is a **per-turn** function: candidate speaks → STT → LLM (with growing history) →
TTS → response, called once per exchange during what PRD §5.3 calls a "Live AI-moderated" or
"Asynchronous" interview. This is a different shape from every AI call shipped so far — M3's
question generation and M1's résumé parsing are both single one-shot batch calls triggered by a
recruiter action, tolerant of a few seconds' latency and fully decoupled from any live person
waiting mid-conversation. M4's calls are turn-by-turn, latency-sensitive to the person actually
in the interview, and stateful across many turns within one session. This ADR exists because
that difference changes which execution model is actually correct — the roadmap's own framing
is tested against it below, not assumed.

**Confirmed by reading the actual function** (`app/services/interview_pipeline.py`):

```python
async def run_turn(history: list[dict], candidate_audio: bytes, audio_format: str = "wav") -> InterviewTurnResult:
    transcript = await transcribe(candidate_audio, audio_format=audio_format)
    history = [*history, {"role": "user", "content": transcript}]
    ai_text = await chat_completion(history, ...)
    history = [*history, {"role": "assistant", "content": ai_text}]
    ai_audio = await synthesize(ai_text)
    return InterviewTurnResult(transcript=transcript, ai_text=ai_text, ai_audio=ai_audio, history=history)
```

Two things this confirms that the first pass of this ADR reasoned about more abstractly:
`run_turn` is **already stateless** — `history` in, updated `history` out, no internal state —
so externalizing it to Postgres is a caller-side addition, not a pipeline refactor. And each of
the three calls (`transcribe`/`chat_completion`/`synthesize`) opens its **own**
`httpx.AsyncClient(timeout=60)` in its respective module (`stt_client.py`, `llm_client.py`,
`tts_client.py`) — three separate TCP/TLS handshakes to `openrouter.ai` per turn instead of one
reused connection. See Migration and rollout.

## Decision drivers

- The roadmap's stated M4 concept is background-job architecture — this ADR verifies that
  framing fits what M4 actually requires before building against it.
- PD-001 already decided the near-term interview experience is **asynchronous**: the candidate
  records answers to questions one at a time, not a live back-and-forth. PRD §5.3 lists "Live
  AI-moderated" as a separate, explicitly stretch-for-MVP mode.
- Cost-sensitive POC (PD-002) — no budget or appetite for standing up Redis/Celery
  infrastructure ahead of a concrete requirement it solves.
- No load or latency data exists yet (R-002, IA-002 unmeasured) — any choice here is provisional
  until a real number exists.
- Session state today is a bare in-process Python object with no persistence and no
  multi-worker safety. This must be resolved regardless of which option is chosen.

## Considered options

### Option 1: FastAPI `BackgroundTasks` for the whole cascade
`POST /session/{id}/turn` returns `202 Accepted` immediately; the STT→LLM→TTS chain runs in a
`BackgroundTasks` callback; the candidate polls a `GET` endpoint for the result.

`BackgroundTasks` runs in the same process and event loop as the API — it does not survive a
server restart, does not distribute across worker processes, and a slow background task still
consumes that process's resources. It solves "don't make the HTTP client wait for the response,"
not "don't burden the server" — and for a live conversational turn, a poll loop is a worse
experience than just waiting on the request, not a better one.

### Option 2: Celery + Redis
STT/LLM/TTS calls dispatched as Celery tasks against a Redis broker, workers scaled
independently of the API process.

Excellent fit for decoupled, retryable, delay-tolerant work — e.g., M5's aggregated
post-interview report. Poor fit for a live per-turn loop: introduces a queue-and-poll round
trip into every conversational exchange, for a workload that is *not* decoupled from the
requester by definition — the candidate is waiting, synchronously, because it's a live
interview. Also introduces new infrastructure (Redis), a new operational dependency, and new
failure modes (queue backlog, worker starvation) for a requirement that doesn't call for it —
exactly the "extra queue without an explicit requirement" pattern this project's own
`product-architect.md` persona flags as overengineering.

### Option 3: WebSocket session, calls awaited inline, responses streamed
A `WebSocket /session/{id}` connection stays open for the interview's duration. Each utterance
triggers STT→LLM→TTS awaited inline in the same async handler — FastAPI's `async def` already
yields the event loop during `httpx`'s I/O-bound awaits, no new concurrency primitive required
for a single conversation — with partial results (interim transcript, streamed LLM tokens,
streamed audio) pushed to the client as they arrive instead of waiting for the full round trip.

Matches PRD §5.3's "Live AI-moderated" mode directly: perceived latency drops because the
candidate sees/hears progress instead of a blank wait. Session state still lives in that one
worker process for the connection's lifetime — same limitation as Option 1 unless externalized
(see Decision) — but the *transport* now matches the actual interaction pattern. No new
infrastructure dependency: WebSocket support is already in the installed `fastapi`/
`uvicorn[standard]` stack.

### Option 4: Fully synchronous HTTP endpoint (current script pattern, exposed) — no new
execution model
`POST /session/{id}/turn` awaits the full STT→LLM→TTS chain inline and returns the complete
result — exactly what `scripts/test_interview_pipeline.py` already does today, wrapped in an
endpoint.

Functionally correct for PD-001's asynchronous mode: the candidate submitted one answer and
isn't watching a live progress indicator, so a several-second wait is acceptable. Cheapest
possible option — zero new code beyond persistence and a router. Does not solve the "Live
AI-moderated" mode's latency-perception problem, but that mode is explicitly stretch/not-MVP,
so it may not need solving in this milestone at all.

## Decision

**Option 4 now, for the asynchronous mode PD-001 actually scoped; Option 3 later, only when the
"Live AI-moderated" mode is scheduled for real.** Do not introduce Celery/Redis for M4 — no
requirement in front of this milestone justifies it, and it would solve a problem (decoupled,
retryable background work) M4 doesn't have. Reserve Celery/Redis as the answer for M5's
aggregated-report generation, which genuinely is delay-tolerant batch work.

**Persistence**: write each turn to Postgres synchronously, inline, in the same request cycle
as the cascade call. The write itself costs milliseconds against calls that already cost
seconds — backgrounding it adds complexity for no measurable benefit.

**Persistence ordering (added on failure-simulation review, 2026-08-10) — this is load-bearing,
not an implementation detail**: persist the candidate's raw submission as a `pending` turn row
**before** calling STT/LLM/TTS, keyed by `(session_id, turn_index)` as a natural idempotency
key — then update that same row with the transcript and AI response once the cascade completes.
Persisting only *after* a successful full round trip (the naive reading of the paragraph above)
has two concrete failure modes: (1) an AI-call failure mid-cascade loses the candidate's answer
entirely — they re-answer with no way to know their first answer didn't count; (2) the
three-call chain's worst-case latency (60s timeout × 3, confirmed in `stt_client.py`/
`llm_client.py`/`tts_client.py` — up to 180s) exceeds realistic browser/proxy client timeouts,
so a client-side retry can race a still-running server request with no way to recognize it's
the same logical turn. The idempotency key resolves both: a retry finds the existing pending
row instead of creating a second one, and a mid-cascade failure leaves the candidate's actual
answer recoverable rather than lost. This also closes a connection-pool risk sharper than R-002
originally stated: holding one DB session open across a full 180s-worst-case cascade would let a
handful of concurrent slow turns exhaust `app/db.py`'s unconfigured connection pool (SQLAlchemy
defaults: 5 + 10 overflow), degrading unrelated requests (jobs, candidates) that have nothing to
do with M4. Persist-before means the initial DB session closes immediately; only a short
second write happens after the cascade.

**Session state**: externalize it. `interview_pipeline.py`'s in-memory `history: list` must
become a DB-backed read (prior turns loaded from the new persisted-turns table at the start of
each `run_turn` call) rather than an in-process object — required under *either* transport
option, because the moment the API process restarts or runs with more than one uvicorn worker,
an in-memory session becomes unreachable. This resolves R-010 (unbounded in-memory growth) as a
side effect of doing persistence correctly, not as a separate future fix.

## Rationale

The roadmap's "BackgroundTasks stops being enough → Celery+Redis" framing is the right *lesson*
— background-job architecture is a real, teachable system-design concept — attached to the
wrong *milestone*. M4's actual requirement is a live, stateful, multi-turn conversation: a
transport/streaming problem, not a queueing problem. Solving it with a task queue would satisfy
the letter of the roadmap's stated concept while making the live-interview UX worse (adds
latency, adds a poll loop) and the system more complex (new infra, new failure modes) with no
load number anywhere to justify it. The queueing lesson already has a real home identified in
this same roadmap — M5's report generation — where the actual requirement (decoupled,
retryable, not latency-sensitive to a live person) exists.

## Consequences

### Positive
- No new infrastructure dependency for M4 — ships on the current stack.
- Matches the actual interaction pattern instead of forcing a batch-job shape onto it.
- Externalizing session state to Postgres resolves R-010 as a byproduct of the milestone's own
  persistence work, not a separate task.
- Keeps Celery/Redis available as a clean, justified answer for M5 instead of introducing it
  prematurely here and then having to explain why M4 doesn't actually use it that way.

### Negative
- WebSocket handling is new surface area for this codebase — no existing WS code to build on,
  some learning/implementation cost when Option 3 is eventually built.
- Two different execution shapes will exist for two different AI-call patterns (synchronous
  await for one-shot generation like M3; WebSocket-streamed for live turns, later). Needs to be
  documented clearly in [[Backend Overview]] so it reads as a deliberate distinction, not
  inconsistency.

### Risks
- No latency measurement exists yet. If a full STT→LLM→TTS round trip for the configured models
  turns out short enough (~1–2s) even without streaming, Option 3's added complexity may not be
  justified even for the live mode, and Option 4 could cover both PRD modes for longer than
  currently assumed — the Validation plan below is what actually settles this, not this ADR.
- Externalizing session state adds a DB read/write to every turn — negligible next to the AI
  calls themselves, but worth confirming once real latency numbers exist.

## Validation plan

1. **Before implementing anything**: instrument `scripts/test_interview_pipeline.py` with timing
   and record p50/p95 for a single turn against the configured `interview_llm_model`. This is
   IA-002, already identified in `docs/implementation-actions.md` and still not started — it is
   now a hard prerequisite for confidently choosing between Option 3 and Option 4 for the live
   mode, not just a nice-to-have.
2. Ship Option 4 (synchronous endpoint + Postgres persistence) for the asynchronous-recording
   mode first — it's the mode actually scoped for near-term delivery per PD-001.
3. Only build Option 3 (WebSocket streaming) once the "Live AI-moderated" stretch mode is
   actually scheduled — validate the need against step 1's latency number at that time, not
   preemptively.
4. **Concrete threshold, not just "measure and see"**: if step 1's p95 for a full cascade turn
   exceeds roughly 25–30s — the realistic ceiling before typical browser `fetch`/proxy timeouts
   start firing, well under the 180s worst case the current per-call timeouts allow — Option 4
   as "wait for the one full response" is not viable even for the asynchronous mode. That
   outcome doesn't necessarily mean building Option 3 early; it may mean tightening per-call
   timeouts and adding client-side retry/backoff first, which is cheaper. Either way, this
   number is what actually decides it, not a hunch.

## Migration and rollout

- New `interview_sessions` / `interview_turns` tables — **not** `sessions`: that name is already
  taken by `app/models/session.py`, the admin-auth login session added for the master-admin
  module. Reusing it would collide both in the schema and in anyone's mental model of what "the
  Session model" means in this codebase. Exact columns are an implementation detail for the M4
  build, not this ADR — expected shape: `session_id`, `interview_id`, `turn_index`, candidate
  transcript/audio ref, AI response text/audio ref, a `status` field (`pending` → ... →
  `complete`, not a boolean), `created_at`. Additive migration, no existing table altered.
- **Transport-agnostic contract (this is what makes the "schema doesn't need to change when the
  transport does" claim checkable, not just intended)**: `interview_turns` rows are outcome-
  shaped — what was said — never delivery-shaped (no queue position, no stream offset, nothing
  that only makes sense for one transport). `(session_id, turn_index)` is the idempotency key
  Option 4's handler uses to survive client retries; Option 3's handler, when it exists, resumes
  or reconnects against the exact same key and terminates by writing to the exact same row. If a
  future implementation needs a second table or a parallel schema to support streaming, this
  contract was violated — that is the concrete test, not a judgment call at the time.
- Design the persisted shape against the frontend contract that already exists and is currently
  unfulfilled: `frontend/src/data/types.ts` defines `SessionInfo` and `ChatMessage` with no
  backend counterpart today. Build M4's schema to satisfy those types (or revise them
  deliberately) rather than letting a third, uncoordinated shape emerge.
- `interview_pipeline.py::run_turn` changes from an in-memory `history: list` parameter to
  reading/writing `interview_turns` rows. This is a behavioral change to an already-standalone,
  unwired module — it carries no risk to any currently-shipped endpoint. The function's
  signature needs no refactor — it already takes/returns `history` rather than owning it.
- New router exposing the synchronous turn endpoint for Option 4 now; a WebSocket endpoint added
  later, additively, when Option 3 is scheduled.
- **Independent of the above, do first**: replace the three per-call `httpx.AsyncClient`
  instances in `stt_client.py`/`llm_client.py`/`tts_client.py` with one shared, connection-pooled
  client reused across a turn's three calls. This is a free latency win that doesn't depend on
  which transport option ships — and IA-002's eventual latency measurement should run *after*
  this fix, not before, or the recorded number won't reflect the design actually being shipped.

## Rollback or exit strategy

Both options are purely additive (new table, new router) — nothing existing is modified, so
rollback is deleting the new migration and router with no data-loss risk to anything currently
in production use (there is none yet). If Option 4 turns out insufficient even for the
asynchronous mode, the persisted-turns schema is reusable by Option 3 unchanged — only the
transport layer would need to change.

## Revisit triggers

- Validation-plan p95 for a full cascade turn exceeds ~25–30s (see Validation plan step 4) —
  Option 4 as "wait for the one full response" stops being viable even for the asynchronous
  mode; revisit timeout/retry tuning before jumping straight to Option 3.
- The "Live AI-moderated" mode gets scheduled for real — triggers building Option 3.
- M5's report-generation work starts — that is the trigger for introducing Celery+Redis, on its
  own merits, not M4's.
- Concurrent session count in dev/demo use exceeds what a single uvicorn worker handles
  comfortably — revisit whether state externalization needs to go further than "read from
  Postgres each turn" (e.g., sticky routing, a shared cache).

## Unresolved questions

- Exact schema for the turns/session tables — deferred to implementation.
- Whether the STT/LLM/TTS calls within one turn should ever run partially concurrently (e.g.,
  prefetching) — a latency-optimization question that only matters once real numbers exist.
- **Audio storage — closed as a question, opened as a hard dependency.** `app/storage/local.py`
  (local disk, no encryption) is the only existing precedent, and R-006's PII/retention gap
  applies to interview audio at least as much as to résumés — arguably more, since voice is more
  sensitive than a résumé file. This is **not** deferrable past M4's build: a real decision
  (where audio lives, whether it's encrypted at rest, what the retention/deletion path is) is
  required before M4 ships, not an open question to carry forward. Tracked via R-006/IA-008;
  M4's build should not proceed without it being resolved, not just acknowledged.
