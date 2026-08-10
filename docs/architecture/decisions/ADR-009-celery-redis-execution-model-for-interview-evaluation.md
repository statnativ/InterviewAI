# ADR-009: Celery + Redis as M5's execution model for interview evaluation

- Status: Accepted
- Date: 2026-08-11
- Owners: Amit Tiwari
- Related product decision: none yet
- Supersedes: none
- Superseded by: none

## Context

M5 ("Answer evaluation + aggregated report, human override") needed to score a completed
interview transcript against the linked job's rubric — the same LLM-as-judge shape
`app/services/candidate_judge.py` already uses for résumé scoring, fed a transcript instead of a
profile. The question this ADR actually settles isn't *what* runs (that's a straightforward
port of an existing pattern) but *how* it gets triggered and executed.

Two proven, in-repo precedents already exist for "run an AI call off the request path":
`POST /candidates/{app_id}/judge` (IA-003) uses FastAPI `BackgroundTasks` + polling
`GET /candidates/{app_id}`, and it's the same pattern `interview_sessions.py`'s router already
imports for other purposes. Reusing it a third time would cost zero new infrastructure.

Against that, `ADR-007` (written during M4 planning, 2026-08-10) explicitly pre-committed to a
different answer for this exact milestone: *"Reserve Celery/Redis as the answer for M5's
aggregated-report generation, which genuinely is delay-tolerant batch work"* — reasoning that
M4's live, turn-by-turn conversation was the wrong shape for a task queue (queueing would make a
candidate wait on a poll loop mid-conversation), but that a real queue was the *right* fit for
whatever ran after an interview was already over, with no candidate waiting on the result. M5 is
that later milestone, and its own roadmap-table teaching concept is literally "pipeline
orchestration" — this project's explicit premise (`Project Overview.md`) is learning system
design concepts by building the thing that needs them, not proxying them.

## Decision drivers
- ADR-007's own forward reference — this is the trigger condition it named, not a fresh
  decision made in a vacuum.
- The roadmap's own teaching-concept framing for M5 ("pipeline orchestration") — a third
  `BackgroundTasks` use would be cheaper but would skip the concept this milestone exists to
  teach, working against the project's stated learning goal.
- Genuine batch-work shape: evaluation has no caller waiting synchronously (unlike M4's
  cascade), no result needs to reach an open HTTP response, and retry/redelivery semantics are
  a real match for what a broker gives you for free.
- Cost-sensitivity (PD-002): Redis is a lightweight, zero-license-cost addition to the existing
  Docker Compose stack, not a hosted managed service — consistent with the project's "local,
  cheap, real" infra choices so far (`ADR-001`).

## Considered options

### Option 1: Reuse `BackgroundTasks` + polling (IA-003's pattern)
Zero new infrastructure. `POST /interview-sessions/{id}/evaluate`-equivalent trigger points
already exist as commit-time hooks in `interview_sessions.py`; a background task could run
`evaluate_interview` the same way `_run_judge_in_background` runs `judge_candidate`.

### Option 2: Celery + Redis
A real broker (Redis) and a real worker process (Celery), run as a fourth piece of local infra
alongside Postgres, uvicorn, and Vite. The router enqueues a task; a separate worker process
picks it up and runs `evaluate_interview`.

### Option 3: A bespoke polling table (no broker)
A `pending_evaluations` table the router inserts into and a standalone script polls on an
interval — reinvents a subset of what Celery/Redis already do, with none of the built-in
retry/visibility tooling.

## Decision

**Option 2 — Celery + Redis**, per ADR-007's own pre-commitment and the milestone's teaching
concept. `docker-compose.yml` gained a `redis` service (broker-only, no result backend
configured — `app/celery_app.py` persists everything to Postgres directly, matching this
codebase's existing "state lives in the database, not the queue" discipline from IA-003).

## The load-bearing implementation finding

The design that shipped is **not** "one fresh `asyncio.run()` (and, in an earlier draft, one
fresh SQLAlchemy engine) per Celery task." That looked correct in isolation but only fixes half
a real bug this codebase has already hit once: `app/db.py`'s module-level async engine binds to
whichever event loop is running the first time it's used (`Backend Overview.md`'s bug #12,
`pytest`'s per-test-function loop default, worked around there with
`loop_scope="session"`). A Celery worker persists across many tasks in one process; tearing a
loop down and recreating it every task breaks that binding on the second task.

A design-review pass caught the second half of the same bug before it shipped:
`app/services/llm_client.py`'s `get_http_client()` is a **second**, independent lazy
module-level singleton (a shared `httpx.AsyncClient`, added for `ADR-007`/`IA-014`'s connection-
pooling win) — every other AI call in this app goes through it. A fresh-engine-per-task fix
would leave this second singleton exposed to the identical failure the moment a worker ran a
second task.

The fix that closes both gaps at once, and the one that actually shipped: **one persistent
event loop per Celery worker *process***, created once in a `worker_process_init` signal
handler (fires after the prefork fork, so there's no fork-inherited-connection risk) and reused,
unclosed, for every task that process ever runs. `app.db.engine`/`async_session` and
`llm_client`'s shared HTTP client both then stay bound to one stable loop for the worker's whole
lifetime, completely unmodified — no per-service special-casing, no new engine, no per-task
teardown. See `app/celery_app.py`.

For local/demo use, the worker runs as `celery -A app.celery_app worker --loglevel=info
--pool=solo` — a single process, no prefork concurrency, no fork-safety concerns at all
(`worker_process_init` still fires once). Documented as the deliberate local choice in
`Runbook.md`; a prefork pool is the production-shape answer if concurrent evaluation throughput
ever needs it, not built here.

## Rationale

Option 1 was the cheaper, lower-risk choice in isolation, and would have worked — but choosing
it here would have quietly walked back ADR-007's own reasoning for treating M4 and M5
differently, and would have skipped the one new system-design primitive this milestone's
roadmap entry names. Option 3 was rejected as strictly worse than Option 2 along every axis that
matters (less tooling, same new-moving-part cost, no real advantage) — if a broker's going to
exist at all, using an established one (Celery/Redis) beats hand-rolling a weaker version of the
same idea.

## Consequences

### Positive
- A real, inspectable "pipeline orchestration" example now exists in this codebase — matching
  the project's own stated learning goal, not just its shipped feature list.
- The persistent-loop pattern is reusable as-is for any future Celery task this project adds —
  no per-task-type loop-safety analysis needed going forward.
- Evaluation retries are cheap and explicit (`POST /interview-sessions/{id}/evaluate`, a manual
  re-enqueue backstop) without inventing new retry machinery.

### Negative
- **A new architectural invariant is now false.** Multiple docs (`Runbook.md`, `Backend
  Overview.md`, `Project Overview.md`) stated "nothing runs as a permanent background service
  except Postgres" — a Celery worker (and Redis) are now real processes that must be running for
  evaluation to happen, not covered by that sentence anymore. Updated in this same change.
- A fourth local process to remember to start (`docker compose up -d` for Redis, plus the
  worker itself) — a real day-to-day friction cost for a solo/local project, accepted the same
  way Postgres-via-Docker already was (`ADR-001`).
- No result backend means Celery's own task-result API can't be queried for status — acceptable
  because nothing needs it (the router polls Postgres), but worth stating so a future reader
  doesn't assume `AsyncResult` works here.

### Risks
- If the worker isn't running, evaluations queue in Redis and never complete — surfaced to the
  recruiter as `evaluationStatus: "pending"` indefinitely, not a hard failure, but a silent-until-
  investigated gap. `R-009` (operational readiness, local-only, no monitoring) already covers
  this class of risk; extended rather than given a new number.
- Redis has no persistence volume configured (broker-only) — a Redis restart with queued-but-
  unpicked-up tasks loses them. Acceptable for a POC with `POST .../evaluate`'s manual retry as
  the backstop; would need addressing (e.g. `appendonly` persistence) before any real deployment.

## Validation plan

Live-verified against the real API and a real worker process, not just the mocked test suite
(`tests/test_interview_evaluation.py`): a genuine Voice-mode interview was run end-to-end
through `docker compose up -d` (Postgres + Redis) and a real
`celery -A app.celery_app worker --pool=solo` process — session creation, one real STT→LLM→TTS
turn, explicit completion, and the resulting `evaluate_interview_task` was picked up by the
worker and completed in ~2.8s with a real OpenRouter call, producing a real per-criterion
scorecard, strengths/gaps, and verdict. The recruiter-facing report page (`InterviewReport.tsx`)
rendered that live result, including audio playback via the new authenticated blob-URL pattern
(`app/routers/interview_reports.py`'s media endpoint) and the human-override decision buttons.

## Migration and rollout

`docker-compose.yml` gained a `redis` service. `requirements.txt` gained `celery[redis]==5.4.0`.
`app/config.py` gained `redis_url`. No database migration beyond the additive
`interview_sessions` columns already covered by
`migrations/versions/e1f2a3b4c5d6_interview_session_evaluation.py`.

## Rollback or exit strategy

If Celery/Redis ever proved to be the wrong call, the fallback is Option 1 (`BackgroundTasks`)
— `evaluate_interview()` itself is broker-agnostic (it's a plain async function; only
`app/celery_app.py`'s task wrapper and the three `.delay()` call sites in
`interview_sessions.py` would need to change), so reverting is a small, contained diff, not a
rewrite.

## Revisit triggers
- The worker ever needs real concurrency (multiple evaluations genuinely queueing up) — the
  point to switch `--pool=solo` to prefork and actually reason about fork-safety beyond "it
  hasn't been needed yet."
- A production deployment (M6b) — the point to add Redis persistence and worker process
  supervision (systemd/Docker restart policies), neither of which exists today.

## Unresolved questions
- Whether Celery Beat (scheduled tasks) or a second queue/routing scheme will ever be needed —
  nothing in scope today calls for either; deliberately not built.
