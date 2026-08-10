---
tags: [project, system-design, python, fastapi, backend]
status: current — ATS vertical slice + M6 Phase 1/2 (tenants, RBAC) wired + master admin auth module + M3 (AI question generation) + M4/M4b (voice + video cascade wired into the app) + M5 (evaluation + report + human override, Celery+Redis) + M2 (LLM-as-judge scoring, moved off the request path via IA-003)
last-updated: 2026-08-11
---

# The Interview Agent — Backend Overview

Companion to [[Project Overview]] (mission + roadmap) and [[AI Architecture]] (how the AI
calls work). This note is the deep dive on the Python/FastAPI backend: stack, data model,
API surface, services, request traces, tests, and the bugs that shaped the code.

Run commands live in [[Runbook]].

## Stack

- **API**: FastAPI, async throughout (SQLAlchemy 2.0 async + asyncpg).
- **DB**: PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16` in Docker, port **5433** —
  5432 was already taken locally).
- **Migrations**: Alembic.
- **AI**: all AI calls go through OpenRouter (see [[AI Architecture]]). The ATS screening
  path itself is **deterministic** — no AI on the request path for scoring.
- **Postgres and Redis are the only permanent background services** (**M5** added Redis, as
  Celery's broker for interview evaluation — see ADR-009) — the API server, the Celery worker,
  and scripts are all started manually ([[Runbook]]).

## Directory map

```
app/
├── main.py            # FastAPI app: CORS, routers, import app.models
├── config.py          # .env → typed settings object (single import point)
├── db.py              # async engine + get_db() dependency
├── celery_app.py      # M5 — Celery app + the persistent-event-loop-per-worker pattern (ADR-009)
├── deps.py            # get_current_tenant / get_current_user / require_roles (M6 P1/P2)
│                      # + require_platform_admin (master admin session cookie, additive)
│                      # + get_current_interview_session (M4 — candidate-facing, session-id-as-
│                      #   credential, deliberately not the tenant/role pattern above)
├── seed.py            # idempotent seed loader (python -m app.seed) — also seeds the one
│                      # platform admin (statnativ)
├── models/            # SQLAlchemy models (all registered in models/__init__.py)
│                      # + session.py, practice_test.py (master admin module)
│                      # + interview_session.py, interview_turn.py (M4, evaluation/decision cols M5)
├── routers/           # health, jobs, candidates, interviews + auth.py, admin.py
│                      # + interview_sessions.py (M4 — candidate-facing, no tenant/role auth)
│                      # + interview_reports.py (M5 — recruiter-facing, tenant/role-scoped)
├── schemas/           # Pydantic view schemas — match frontend TS types 1:1
│                      # + auth.py, admin.py schemas
│                      # + interview_session.py (M4), interview_report.py (M5)
├── services/          # business logic (kept out of the HTTP layer) + authz.py (RBAC matrix)
│                      # + question_generator.py (M3 — LLM question generation)
│                      # + llm_scoring.py (M5 — shared JSON-coercion logic)
│                      # + interview_evaluator.py (M5 — scores a completed transcript)
├── storage/           # local.py — uploaded file storage (+ save_interview_audio, M4)
migrations/            # Alembic (env.py imports app.models wholesale)
tests/                 # pytest: test_health, test_screening, test_tenant_isolation, test_rbac,
                        # test_admin_auth, test_question_generation, test_ai_client_resilience,
                        # test_candidate_judge, test_interview_sessions, test_interview_evaluation
scripts/                # standalone tools (synthetic corpus, voice-cascade demo)
```

## Data model — 15 tables

Full ATS schema, with pgvector embeddings on `resumes`/`skills` and GIN full-text search on
`resumes.raw_text`. Six of the original eleven tables carry `tenant_id` (M6 Phase 1) —
`tenants` itself is the only fully global table; `skills`/`resume_skills`/`job_skills`/
`ai_processing_logs` stay untenanted (shared taxonomy / join tables that inherit isolation
through their parent FKs). Two more tables (`sessions`, `practice_tests`) were added by the
master admin auth module — see the addendum in [[Identity & Access Overview]]. Two more still
(`interview_sessions`, `interview_turns`) were added by M4 — see below.

| Table | Model file | Purpose |
|---|---|---|
| `tenants` | `tenant.py` | **New (M6 Phase 1)**: `name`, `slug` (unique), `created_at`. One row per company; every tenant-scoped table below FKs into this. One seed row today (Northwind Health, `SEED_TENANT_ID` in `app/deps.py`). |
| `users` | `user.py` | `tenant_id` (**nullable** as of the admin auth module — `NULL` means a platform admin, enforced by `ck_users_platform_admin_no_tenant`), `email` (UNIQUE **per tenant**, not globally — changed in migration `c3d4e5f6a7b8`), `name`, `role` (admin/recruiter/hiring_manager — now **enforced**, see Services below), plus `username`/`password_hash` (nullable, admin-managed accounts only), `status` (pending/active/disabled), `is_platform_admin`. Tenant users still have no real auth; `X-User-Email` dev header resolves identity. The one platform admin logs in for real via `/auth/login` — see [[Identity & Access Overview]] addendum. |
| `sessions` | `session.py` | **New (admin auth module)**: `id` (UUID, doubles as the opaque session cookie value — not hashed, a noted POC simplification), `user_id` (FK, CASCADE), `created_at`, `expires_at`. Currently only used for platform-admin logins. |
| `practice_tests` | `practice_test.py` | **New (admin auth module)**: `tenant_id` (FK, NOT NULL — tenant-scoped), `title`, `mode` (Chat/Voice/Avatar), `status` (Draft/Active/Archived), `questions` (JSONB), `duration`. Authored by the platform admin via `/admin/practice-tests`. |
| `jobs` | `job.py` | `tenant_id` + the JD: `description`, `department`, `requirements`, `location`, `employment_type`, `experience_level`, `salary_min/max`, `currency`, `status`, `posted_by`, plus **`rubric` (JSONB)** and **`versions` (JSONB)** — the frontend contract. |
| `candidates` | `candidate.py` | `tenant_id` + full ATS profile: identity (`name`, `email` UNIQUE **per tenant**, `phone`, `location`, `linkedin_url`, `portfolio_url`), sourcing (`source`, `tags`, `notes`), and the extracted resume (`resume_file`, `years_exp`, `current_title`, `current_company`, `skills`, `summary`, `experience`, `education`, `certifications` — JSONB). |
| `resumes` | `resume.py` | `tenant_id` + `file_path`, `raw_text`, `parsed_data` (JSONB), `embedding` (`Vector(1536)`), `ai_summary`, `ai_strengths`/`ai_concerns`, `years_experience`, `seniority_level`, `is_primary`. Indexes: ivfflat (embedding), GIN (raw_text), partial `(candidate_id, is_primary)`, plus `tenant_id`. |
| `skills` | `skill.py` | Taxonomy: `name`, `category`, `aliases` (array), `embedding`. ivfflat index. Not wired to endpoints yet. Deliberately **not** tenant-scoped — shared vocabulary, not customer data. |
| `resume_skills`, `job_skills` | `resume_skill.py`, `job_skill.py` | Many-to-many joins (composite PKs, no surrogate id). Not wired to endpoints yet. Not tenant-scoped directly — isolation comes transitively through `resume_id`/`job_id`. |
| `applications` | `application.py` | `tenant_id` + the screening record: `candidate_id`+`job_id`+`resume_id`, `status`, `stage`, `match_score`, `match_breakdown` (JSONB, still unused), plus screening outputs **`shortlisted`, `decision`, `pipeline_stage`, `scorecard` (JSONB), `strengths`/`gaps` (string arrays), `compare_verdict`, `ai_note`**, and **`score_method`** (`deterministic`/`llm_judge`, `CHECK ck_applications_score_method`, real column + constraint from day one, not inferred — see the LLM-as-judge section below). **`judge_status`/`judge_error`** (new — IA-003: `idle`/`pending`/`failed`, `CHECK ck_applications_judge_status`, `judge_error` nullable `Text`) — real, pollable state for the backgrounded judge call, since failure can no longer surface as a synchronous HTTP error. Fully wired. |
| `interviews` | `interview.py` | `tenant_id` + `title`, `job_title` (plain string, kept as a display fallback), `job_id` (**new, M3** — nullable FK to `jobs`, resolves the [[UX Review]] finding #10 IA gap), `candidate_id` (**new, M3** — nullable FK to `candidates`; set means this interview is personalized for one person, not a shared template), `mode` (Chat/Voice/Avatar), `status` (Draft/Active/Archived), `questions` (JSONB), `duration`, `shared`. **`CHECK ck_interviews_no_shared_personalized`** (new, R-011/IA-012): `shared` and `candidate_id IS NOT NULL` can't both be true — prevents a personalized interview from being broadcast to every applicant. No `scheduled_at` column despite an earlier version of this note claiming otherwise. |
| `ai_processing_logs` | `ai_processing_log.py` | Audit trail for AI calls (model, tokens, cost, success/failure). Table exists, not yet written to. Not tenant-scoped yet — would need it before this becomes a real audit trail (M6 Phase 6). |
| `interview_sessions` | `interview_session.py` | **New (M4), extended (M5)**: `tenant_id`, `interview_id`, `candidate_id` (nullable — a `shared` interview link has no candidate to attribute the session to), `status` (`active`/`complete`/`abandoned`, `CHECK ck_interview_sessions_status`). `id` doubles as the bearer credential for every turn request (ADR-008) — no candidate login exists anywhere in this codebase. **M5** added the AI-evaluation output — `evaluation_status` (`idle`/`pending`/`complete`/`failed`, `CHECK ck_interview_sessions_evaluation_status` — a deliberate 4-state design, richer than `judge_status`'s 3-state precedent), `score`, `scorecard` (JSONB), `strengths`/`gaps` (arrays), `ai_verdict`, `ai_note`, `evaluation_error`, `evaluated_at` — plus the human-override `decision` (`None`/`Approved`/`Hold`/`Rejected`, no CHECK, mirrors `applications.decision`'s exact precedent, and never touched by the AI-evaluation fields above it). |
| `interview_turns` | `interview_turn.py` | **New (M4)**: `session_id` + `turn_index` (client-supplied, `UNIQUE(session_id, turn_index)` — the idempotency key ADR-007's persist-before-calling pattern depends on), `status` (`pending`/`complete`/`failed`, `CHECK ck_interview_turns_status`), `candidate_audio_path`/`candidate_audio_format`, `transcript`, `ai_text`, `ai_audio_path`, `error`. Audio paths point at unencrypted local disk (`data/interview_audio/`) — a deliberate, risk-accepted extension of R-006, recorded in ADR-008. **`media_type`** (new, M4b — `String(20)`, `'audio'`/`'video'`, `CHECK ck_interview_turns_media_type`): the *columns* weren't renamed when video capture shipped — `candidate_audio_path`/`candidate_audio_format` hold whichever media the candidate uploaded, `media_type` is what records which one, a deliberately additive-not-renamed migration. |

### Schema evolution (the migration story)

- `68b7d2e3a988_init_full_schema.py` — replaced the original 3-table migration: both
  extensions + all 9 original tables/indexes (columns were renamed/added-as-NOT-NULL, so
  layering on top wasn't possible).
- `a1b2c3d4e5f6_align_schema_for_ats.py` — aligned the schema to the frontend contract:
  job rubric/versions, candidate profile columns, application screening columns,
  `interviews` table.
- `c3d4e5f6a7b8_tenant_isolation.py` — M6 Phase 1: new `tenants` table + seed row; `tenant_id`
  added to the six tables above via the standard add-nullable → backfill → not-null pattern
  (written by hand, not autogenerated — this is exactly the kind of migration Runbook.md warns
  autogenerate handles poorly); `users.email`/`candidates.email` moved from global `UNIQUE` to
  `UNIQUE (tenant_id, email)`.
- `d4e5f6a7b8c9_admin_auth_module.py` — master admin auth module: `users.tenant_id` relaxed
  back to nullable; `username`/`password_hash`/`status`/`is_platform_admin` columns added;
  partial unique index `uq_users_username` (`WHERE username IS NOT NULL`); `CHECK` constraint
  `ck_users_platform_admin_no_tenant`; new `sessions` and `practice_tests` tables. Full
  `downgrade()` included.
- `e5f6a7b8c9d0_interview_job_candidate_links.py` — M3: nullable `interviews.job_id`/
  `candidate_id` FKs. `job_id` is backfilled by hand-written SQL matching the existing
  `job_title` string against `jobs.title` **only where unambiguous** (exactly one job with that
  title in the tenant) — left null everywhere else rather than guessing; `candidate_id` gets no
  backfill (new concept, nothing to infer it from).
- `f6a7b8c9d0e1_interview_shared_personalized_check.py` — R-011/IA-012: `CHECK` constraint
  `ck_interviews_no_shared_personalized` — `NOT (shared AND candidate_id IS NOT NULL)`. M3
  shipped candidate personalization without a guard against sharing a personalized interview
  with every other applicant; checked for existing violations (none) before applying.
- `a7b8c9d0e1f2_application_score_method.py` — M2 (LLM-as-judge): adds
  `applications.score_method` (`String(20)`, NOT NULL, default `'deterministic'`) + `CHECK
  ck_applications_score_method` restricting it to `deterministic`/`llm_judge`. Same discipline
  as the interview CHECK above — a real, inspectable column from day one, not inferred state.
- `b8c9d0e1f2a3_application_judge_status.py` — IA-003 (LLM-as-judge off the request path):
  adds `applications.judge_status` (`String(20)`, NOT NULL, default `'idle'`) + `CHECK
  ck_applications_judge_status` (`idle`/`pending`/`failed`) and `applications.judge_error`
  (`Text`, nullable). Same discipline again — a third real, inspectable state-discriminator
  column this session, not an inferred flag.
- `c9d0e1f2a3b4_interview_sessions_and_turns.py` — M4: two new tables, `interview_sessions`
  and `interview_turns` (see Data model above), each with the same `String(20)` + `CHECK`
  status-column discipline, plus `interview_turns`' `UNIQUE(session_id, turn_index)` idempotency
  constraint. Migration docstring cites ADR-007 and ADR-008 for why audio storage is unencrypted
  by deliberate choice, not oversight.
- `d0e1f2a3b4c5_interview_turns_media_type.py` — M4b: adds `interview_turns.media_type`
  (`'audio'`/`'video'`, `CHECK ck_interview_turns_media_type`). Purely additive — the
  `candidate_audio_path`/`candidate_audio_format` columns were deliberately **not** renamed
  despite now potentially holding a video file; a rename would have touched every M4 call site
  for a cosmetic reason, against this project's additive-migration discipline.
- `e1f2a3b4c5d6_interview_session_evaluation.py` — M5: adds `interview_sessions`'
  AI-evaluation columns (`evaluation_status` + `CHECK`, `score`, `scorecard`, `strengths`,
  `gaps`, `ai_verdict`, `ai_note`, `evaluation_error`, `evaluated_at`) and the human-override
  `decision` column (no `CHECK`, mirroring `applications.decision`'s precedent). Purely
  additive — no existing `interview_sessions` column touched.
- `migrations/env.py` does `import app.models` so Alembic and the app can never see
  different slices of the schema (see the bug below that caused this).

> The "no explicit `idx_candidates_email`" deviation from the original SQL no longer applies —
> since the unique constraint is now composite (`tenant_id, email`), an explicit
> `idx_candidates_tenant` index was added alongside it (same for every tenant-scoped table).

## API surface

Full reference lives in Swagger at `http://localhost:8000/docs` (auto-generated from
`app/schemas/`). The map:

| Router | Endpoints |
|---|---|
| `health.py` | `GET /health` |
| `jobs.py` | `GET/POST /jobs`, `GET/PATCH /jobs/{job_id}`, `POST /jobs/{job_id}/regenerate-rubric`, `POST /jobs/{job_id}/save-version`, `GET /jobs/{job_id}/candidates` |
| `candidates.py` | `GET/POST /candidates` (create = dedupe by email + screen instantly), `GET/PATCH /candidates/{app_id}` (polling target for the judge job, below), `POST /candidates/{app_id}/screen` (deterministic), `POST /candidates/{app_id}/judge` (LLM-as-judge — **`202`, not `200`/`502`, as of IA-003**: 400 if the job has no rubric, 409 if already `judge_status="pending"`, otherwise flips the row to `pending` and returns immediately; the actual LLM call and any failure now happen off-request, see below), `POST /candidates/bulk`, `POST /candidates/{app_id}/resume` |
| `interviews.py` | `GET/POST /interviews`, `GET/PATCH /interviews/{iv_id}` (**409**, not a raw 500, if a `PATCH` would violate `ck_interviews_no_shared_personalized` — R-011/IA-012), `POST /interviews/{iv_id}/regenerate` (**new, M3** — replaces the whole question set), `POST /interviews/{iv_id}/questions/{q_id}/regenerate` (**new, M3** — replaces one question in place) |
| `auth.py` | **New (admin auth module)**: `POST /auth/login` (username/password → session cookie), `POST /auth/logout`, `GET /auth/me`. Platform-admin only — see [[Identity & Access Overview]] addendum. |
| `admin.py` | **New (admin auth module)**: `GET/POST /admin/tenants`, `GET/POST /admin/users` + `/admin/users/{id}/approve` + `/admin/users/{id}/disable`, `GET/POST /admin/practice-tests`. Every route behind `require_platform_admin` at the router level (`dependencies=[Depends(require_platform_admin)]`). |
| `interview_sessions.py` | **New (M4), extended (M4b, M5)**: `POST /interviews/{interview_id}/sessions` (open access, keyed on the interview's own unguessable id — creates a session, seeds the opening AI question from the interview's curated questions; accepts `mode IN ("Voice", "Video")` as of M4b, `400` for anything else), `POST /interview-sessions/{session_id}/turns` (the core exchange — persist-before-calling, idempotent on `turn_index`; the uploaded blob's `media_type` is derived from `interview.mode` and stamped on the turn row), `GET /interview-sessions/{session_id}` (reload/resume), `POST /interview-sessions/{session_id}/complete`. **No `get_current_tenant`/`require_roles` on any of these** — see the dedicated callout below. **M5**: all 3 places a session can flip to `status="complete"` now also set `evaluation_status="pending"` and enqueue `evaluate_interview_task` in the same request — see the M5 callout below. |
| `interview_reports.py` | **New (M5)** — recruiter-facing, tenant/role-scoped (unlike `interview_sessions.py` above): `GET /interviews/{interview_id}/sessions` (list, any role), `GET /interview-sessions/{session_id}/report` (full report — score, scorecard, transcript, decision), `PATCH /interview-sessions/{session_id}` (sets `decision`, write-roles only), `POST /interview-sessions/{session_id}/evaluate` (manual retry, `409` if already `pending`), `GET /interview-sessions/{session_id}/turns/{turn_index}/media?speaker=candidate\|ai` — **this app's first file-serving endpoint**. |

Design rules: view schemas are flat and match `frontend/src/data/types.ts` field-for-field
(`app/services/views.py` maps ORM → view); business logic never lives in routers — it's in
`app/services/`.

**`POST /interviews` generates questions automatically (M3)** when `jobId` is given and no
`questions` array is supplied — it looks up the `Job`, optionally resolves `candidateId` to a
real `Candidate` (see `question_generator.py` below), and calls `generate_questions()`
synchronously before persisting the row. A malformed/empty LLM response raises `LLMError`,
which the router turns into a `502` rather than a 500 or a silently-empty question list — the
first place in this codebase an LLM failure is actually caught, not left to bubble up unhandled
(see "Known debt" — `llm_client.py`'s error-handling gap is still open everywhere else).

**Every `jobs`/`candidates`/`interviews` route requires two dev-mode identity headers** (M6
Phase 1/2, `app/deps.py`): `X-Tenant-Id` (defaults to the seed tenant if absent) and
`X-User-Email` (defaults to the seed recruiter). Read routes accept any role; write routes
(`POST`/`PATCH` except on `/interviews`, which stays open to all three roles) require admin or
recruiter — see `app/services/authz.py`. A request with an unrecognized email gets `401`; a
recognized user with the wrong role gets `403`. These headers are explicitly a stand-in for
Phase 3's real session-based auth, not real security — nothing stops a client from claiming any
tenant/email today. **`auth`/`admin` routes are a separate, real-auth surface** (session cookie
via `require_platform_admin`, not the dev headers) — see [[Identity & Access Overview]]
addendum for why this doesn't count as Phase 3 being done. **`interview_sessions.py` routes are
a third, separate surface again** — no headers at all, session-id-as-credential instead (M4,
ADR-008) — see the dedicated callout below.

**`POST /candidates/{app_id}/judge` is this codebase's first-ever use of FastAPI
`BackgroundTasks` (IA-003, 2026-08-10 — confirmed via grep before writing it: zero prior usage).**
The pre-checks (404 candidate/job, 400 no-rubric, 409 already-pending) run synchronously and
fail the request immediately, same as before; once those pass, the row flips to
`judge_status="pending"`, `background_tasks.add_task(_run_judge_in_background, ...)` is
scheduled, and the endpoint returns `202` with that pending snapshot — the LLM call itself runs
*after* the response is already sent. The one detail that had to be gotten right: a
`BackgroundTasks` callable can run after the request-scoped `Depends(get_db)` session has been
torn down, so `_run_judge_in_background` opens its **own** `async with async_session() as db:`
rather than reusing the injected one — the same standalone-session pattern `app/seed.py` already
used outside a request's DI lifecycle, applied inside a background task for the first time. Only
plain IDs/primitives are passed into `add_task(...)`, never ORM objects bound to the closing
session. The background function catches broadly (not just `LLMError`): an uncaught exception
there has no HTTP response to surface through, so it must mark `judge_status="failed"` +
`judge_error` itself or the row is stranded at `"pending"` forever. The frontend polls the
existing `GET /candidates/{app_id}` — no new endpoint was needed, `CandidateView` just gained the
two fields. Scope was deliberately narrow: deterministic scoring (`_apply_screening`, sub-
millisecond, no I/O beyond one DB write) and résumé text extraction (`extract_text`, local
PDF/DOCX parsing) both stay synchronous — backgrounding either would be pure overhead. This is
also explicitly *not* a contradiction of ADR-007's "don't background before there's a measured
need" call on M4: M4's cascade is a live, turn-by-turn conversation where queueing would make the
UX worse; LLM-as-judge is a one-shot, explicit, non-interactive action, and a live measurement
(~8s for one `judge_candidate` call) is exactly the "measured need" ADR-007 said to wait for.

**`interview_sessions.py` is this codebase's first candidate-facing, non-recruiter auth pattern
(M4, ADR-008).** Every other router resolves identity via `get_current_tenant`/`require_roles`
(the `X-Tenant-Id`/`X-User-Email` dev headers) — that pattern assumes a recruiter is calling.
There is no candidate identity anywhere in this app (no login, no header a candidate's browser
would send), so this router uses a genuinely different dependency instead:
`get_current_interview_session` (`app/deps.py`) resolves `session_id` from the URL path, loads
the `InterviewSession` row, and 404s only if it doesn't exist — deliberately **not** calling
`get_current_tenant` (there's no header to trust), with `tenant_id` instead derived transitively
(`interview_id` → `Interview.tenant_id`) once, at session-creation time, and stored directly on
the row. The dependency also deliberately does *not* judge whether the session's current status
is valid for the calling route — that's left to each route (`POST .../turns` on a
`complete`/`abandoned` session is a `409` from the route itself, not folded into the dependency's
404), matching this codebase's existing discipline of keeping "doesn't exist" and "exists but
wrong state" as distinct failure meanings (see `ck_interviews_no_shared_personalized`'s `409`
above).

`interview_sessions.id` (an unguessable UUID, minted at creation) *is* the bearer credential —
no separate token or login system. Session creation itself is keyed on the interview's own id
(already an unguessable UUID, already the frontend's URL param since M3), so there's no
unauthenticated bootstrap step to design around. ADR-008 records this as a deliberate,
risk-accepted choice — consistent with R-001's existing posture for the recruiter side pre-M6 —
not an oversight; R-001 has been extended to note the new surface it now covers.

**The turn endpoint's persist-before-calling idempotency, made concrete** (ADR-007 specified the
pattern; here's exactly how it's implemented): `POST /interview-sessions/{id}/turns` takes a
**client-supplied** `turn_index` — not server-derived from a count, which would defeat the whole
mechanism, since a client retry needs to land on the *same* index to be recognized as a retry,
not a new turn. On each call: an existing `complete` row for that `(session_id, turn_index)`
returns the cached result immediately, without re-running the cascade (avoids double-billing the
LLM/TTS calls); an existing `pending` row means a request for this exact turn is genuinely still
in flight, so it's a `409`; an existing `failed` row is retried (flipped back to `pending`); no
row means one is inserted `pending`, then the DB session is closed *before* the slow cascade call
— two short, separate `async_session()` scopes bracketing the call, matching
`_run_judge_in_background`'s shape above, never one session held open across it (ADR-007's
connection-pool-exhaustion concern: SQLAlchemy's default pool is 5+10 overflow, and the cascade's
worst case is 60s × 3 calls).

**Live-verified against the real API, not just the mocked test suite**: a genuine TTS timeout on
`hexgrad/kokoro-82m` (the same failure mode IA-002/IA-009 already documented) hit exactly the
failed→retry path above — the turn row flipped to `failed` with the real error text captured,
the session stayed `active`, and resubmitting the identical `turn_index` succeeded normally on
retry.

**M4b widened `interview_sessions.py` to a second capture type — and the interesting part is
everything it *didn't* have to change.** The router's mode gate went from `interview.mode !=
"Voice"` to `interview.mode not in ("Voice", "Video")`; `submit_turn` derives `media_type` from
`interview.mode` (fetched once, same call already used for history reconstruction) and stamps it
on the turn row. That's the entire router diff. `interview_pipeline.py` — `start_interview`,
`run_turn`, `build_system_prompt` — needed **zero** code changes, confirmed by the same
Video-mode turns flowing through those unmodified functions in a real end-to-end run: the cascade
only ever sees transcript-derived text, never the media type it came from. This is the concrete,
empirically-proven version of PD-001's "swap the capture type, not the architecture" claim, not
just a restatement of it.

The one genuinely open question going in was whether OpenRouter's STT model would accept a webm
container holding **both** video and audio tracks, or need the video stream stripped first —
`stt_client.py`'s `transcribe(audio_bytes, audio_format)` has always passed `audio_format` through
unvalidated, so nothing in the code enforced audio-only input, but nothing had ever tested the
video case either. Answered empirically the same way M4 validated webm-audio compatibility: a
real `ffmpeg`-synthesized test file (`color=c=blue:s=320x240:d=6` + a sample MP3 track, encoded
`libvpx`/`libopus` into a genuine webm container) was submitted through the actual `POST
/interview-sessions/{id}/turns` endpoint against the live API. `qwen/qwen3-asr-flash-2026-02-10`
transcribed the embedded audio track correctly, no client-side or server-side extraction needed —
the STT leg needed exactly as much code change as the rest of the cascade: none.

**Storage got no video-specific sibling function, on purpose.** `save_interview_audio` was
already `(bytes, filename, session_id) → Path` with zero content-type awareness — reusing it for
video bytes required no new code, just an updated doc comment noting it now handles either media
type. `InterviewTurn.media_type` is what distinguishes audio from video for anything that reads
the data back later.

**M5's trigger wiring is three small hooks, not a rewrite.** All 3 places
`interview_sessions.py` already flips `InterviewSession.status` to `"complete"` (session
creation's rare 1-question-complete branch, `submit_turn`'s normal completion, the explicit
`/complete` early-bail) now also set `evaluation_status="pending"` in that same commit, then call
a small `_trigger_evaluation()` helper that enqueues `evaluate_interview_task.delay(...)`. That
call is wrapped in a broad `try/except`: if enqueueing itself fails (Redis unreachable), the
session is marked `evaluation_status="failed"` with a clear error instead of letting a queueing
problem break the candidate-facing response that had already succeeded — finishing an interview
must never fail because of this side effect.

**The evaluation pipeline's real engineering problem wasn't the LLM call — it was making Celery
and this app's async SQLAlchemy stack coexist safely.** `app/services/interview_evaluator.py`
mirrors `candidate_judge.py`'s exact shape (one `chat_completion` call, strict JSON prompt,
never-trust-the-response coercion — the shared clamp/scorecard logic was extracted into
`app/services/llm_scoring.py` so it isn't duplicated between the two). The genuinely new part is
`app/celery_app.py`: a Celery worker persists across many tasks in one process, and this
codebase already has *two* lazy module-level singletons that bind to whichever asyncio event
loop first touches them — `app.db`'s engine, and `llm_client.get_http_client()`'s shared
`httpx.AsyncClient` (added for `ADR-007`/`IA-014`). A naive fresh-`asyncio.run()`-per-task
design only breaks the second singleton (not the first, if you also give each task a fresh
engine) — an easy way to ship something that looks correct on the first task and fails on the
second. The fix: **one persistent event loop per worker *process***, created once in a
`worker_process_init` signal handler and reused, unclosed, for every task that process ever
runs — both singletons then stay bound to one stable loop for the worker's whole life,
completely unmodified. Full reasoning in **ADR-009**; local/demo runs use
`celery -A app.celery_app worker --pool=solo` (single process, no fork-safety concerns) per that
ADR's recommendation.

**`interview_reports.py` is a deliberately separate router, not an extension of
`interview_sessions.py`** — the latter's whole file-level docstring is about being the
candidate-only, no-tenant-auth surface (ADR-008); mixing a `get_current_tenant`-gated route in
would contradict that documented contract. The new router uses **direct
`InterviewSession.tenant_id` filtering** for its ownership checks (the row already carries it,
set transitively at session-creation time — no join through `Interview` needed), the same
pattern `Application.tenant_id` already uses elsewhere.

**The media endpoint is this app's first file-serving endpoint — and the frontend's answer to
it is a new pattern too.** `GET .../turns/{turn_index}/media?speaker=candidate|ai` returns a
`FileResponse`, `404` (not 500) whenever the requested path is `None` — turn 0 has no candidate
audio at all, and every audio/video path column is nullable. The one thing that had to be solved
on the frontend side: `X-Tenant-Id`/`X-User-Email` are plain custom headers this app's whole
auth model runs on, and a native `<audio src>`/`<video src>` genuinely cannot attach them. The
fix is a `fetch()` call that returns a `Blob`, turned into a `createObjectURL()` the media
element's `src` points at (revoked on unmount/turn-switch) — see [[Frontend Overview]].

## Services — where the logic lives

| Service | Responsibility |
|---|---|
| `authz.py` | **New (M6 Phase 2)**: the RBAC permission matrix as data — `ADMIN`/`RECRUITER`/`HIRING_MANAGER` role constants, `ALL_ROLES`/`WRITE_ROLES` tuples. `app/deps.py`'s `require_roles(*roles)` reads these; routers just declare which tuple a route needs. |
| `screening.py` | **The ATS brain (deterministic)**: `generate_rubric` (draft rubric from a JD, each criterion's description now quoting the actual JD context it matched via `_context_snippet` — was one repeated boilerplate sentence per tag before the [[UX Review]] fix), `derive_score` (weighted coverage vs. rubric), `extract_skills` (against the 163-skill dictionary), `build_strengths`/`build_gaps`, `screen_candidate` (persists scorecard/strengths/gaps/verdict on the application row). Still the free/instant default for candidate creation and résumé upload — untouched by `candidate_judge.py` below. |
| `candidate_judge.py` | **New (M2, LLM-as-judge)**: `judge_candidate` (JD + rubric + a candidate's full structured profile — experience depth, summary, education, certifications, not just `skills` — via one `chat_completion` call, same JSON-mode pattern as `question_generator.py`) reasons per rubric criterion instead of keyword-matching. `_coerce_result` never trusts the raw response: score clamped to `[0,99]` (via `llm_scoring.clamp_int`, **M5**), `shortlisted` computed from the (clamped) score rather than read from the model so it means the same threshold regardless of method. `build_scoring_profile` is a deliberately separate profile builder from `question_generator.build_candidate_profile` (different fields matter for scoring vs. question-writing) and — like that one — omits the candidate's name from the prompt. Explicit, recruiter-triggered, never auto-run on candidate creation. |
| `llm_scoring.py` | **New (M5)**: `strip_fences`, `clamp_int`, and `coerce_scorecard` — extracted out of `candidate_judge.py` once `interview_evaluator.py` needed the identical never-trust-the-LLM clamp/validation logic (weight always from the rubric, a missing criterion raises `LLMError` rather than persisting an incomplete scorecard). Built as a dedicated refactor step *after* both callers worked and were tested, not a speculative shared module written up front. |
| `interview_evaluator.py` | **New (M5)**: `evaluate_interview(session_id)` — scores a *completed* interview's full transcript against the linked job's rubric, the same LLM-as-judge shape as `candidate_judge.py` fed a transcript instead of a résumé profile. Meant to run inside a Celery task (`app/celery_app.py`), not called directly from a router — see the M5 callout above for why. No `job_id`/`Job.rubric` → `evaluation_status="failed"` with a clear message, never raised uncaught (there's no HTTP response left to catch it once this runs in a background task). |
| `skill_dictionary.py` | The 163-skill taxonomy, extracted from the frontend's `src/lib/skills.ts` — the source of truth for skill extraction (multi-word priority, case-insensitive). |
| `views.py` | ORM-model → view-schema mappers (`job_to_view`, `candidate_to_view`, `interview_to_view`, plus **M5**'s `interview_session_to_summary_view`/`interview_session_to_report_view`). |
| `resume_parser.py` | `extract_text` (PDF/DOCX → plain text) — on the ATS upload path. `parse_resume` (LLM → structured JSON) still exists but is **no longer on the ATS path** — screening is deterministic now. |
| `question_generator.py` | **New (M3)**: `generate_questions` (JD + optional candidate profile → 8–12 questions via one `chat_completion` call, same prompt→strip-fences→`json.loads` pattern as `resume_parser.parse_resume`, but raises `LLMError` on bad output instead of falling back), `regenerate_question` (one replacement question, same type/difficulty, avoids duplicating the others), `build_candidate_profile` (compact prompt block from `Candidate`'s already-structured fields — no re-parsing a résumé file). |
| `llm_client.py` | OpenRouter `/chat/completions` via a shared, connection-pooled client (`get_http_client()`, IA-014). Supports `exclude_reasoning=True` to strip a reasoning model's "thinking" from visible output. Response shape validated + a hard-failure retry/fallback (`post_with_retry`, opt-in `fallback_model`) added 2026-08-10 (IA-009) after IA-002 reproduced both failure modes live — depth in [[AI Architecture]]. |
| `stt_client.py` | OpenRouter `/audio/transcriptions`. Model: `qwen/qwen3-asr-flash-2026-02-10`. One same-model retry (IA-009). |
| `tts_client.py` | OpenRouter `/audio/speech`. Model: `hexgrad/kokoro-82m` — **paid**, not free-tier (a prior version of this note miscalled it free-tier). One same-model retry (IA-009) — this is the leg that hit a real 60s timeout during IA-002. |
| `interview_pipeline.py` | Chains STT→LLM→TTS. `start_interview()` + `run_turn()`; conversation history (a list of chat messages) **is** the session state, passed in and returned, not owned by the module. Interviewer brain: `nvidia/nemotron-3-ultra-550b-a55b:free`, with automatic fallback to `deepseek/deepseek-v4-pro` on hard failure (IA-009). **Wired into the app now (M4)** — `app/routers/interview_sessions.py` calls it for real, not just the standalone script. `start_interview()` now takes the interview's own curated `questions` (M3) and builds a system prompt instructing the interviewer to ask them in order with limited follow-ups, ending with a detectable `[INTERVIEW_COMPLETE]` sentinel (`strip_completion_sentinel`) instead of an open-ended, no-termination conversation. New `bound_history()` (IA-004) caps what's sent to the LLM each turn — a pure function, called by the router before `run_turn`, not inside the module itself (`run_turn`'s own signature is unchanged, per ADR-007). |

`app/storage/local.py` saves uploaded files under `data/resumes/{candidate_id}/` with a
random prefix — plus `save_interview_audio` (M4), same pattern, under
`data/interview_audio/{session_id}/`.

## Request traces

**Create a job** — `POST /jobs` → router validates → `generate_rubric` drafts 4 criteria
from the JD → job + rubric + version row persisted → view returned.

**Add a candidate** — `POST /candidates` (multipart, optional resume file) → dedupe by email
(case-insensitive; `409` on duplicates) → `extract_skills` from provided text/resume →
`_apply_screening` runs `derive_score` against the job's rubric → persists candidate +
application (with scorecard/strengths/gaps/verdict) → returns the fully-screened view.

**Upload a resume to an application** — `POST /candidates/{app_id}/resume` → `extract_text`
in `resume_parser` → file saved via `storage/local.py` → skills re-extracted → re-screened
against the job → `Resume` + updated application persisted. Deterministic — no LLM call.

## Tests

```bash
pytest                          # from repo root (venv active) — 95 tests, all DB-backed
                                 # ones run against the real dev Postgres (no test-DB isolation
                                 # layer exists yet; each test cleans up what it creates)
```

- `tests/test_health.py` — liveness endpoint.
- `tests/test_question_generation.py` — **new (M3)**, 9 tests — the suite's first **LLM-mocked**
  tests: `question_generator.chat_completion` is monkeypatched to return canned JSON (a fake
  that tells a "generate N questions" prompt apart from a "regenerate one question" prompt by
  content, same as a real model would respond differently). Covers: 8–12 questions generated
  and persisted on `POST /interviews` with a `jobId`; malformed model output → clean `502`, not
  a 500; `/regenerate` replaces the whole set and `400`s without a `job_id`; single-question
  regenerate replaces exactly one entry; tenant scoping; candidate personalization (asserts the
  candidate's profile text appears in the captured prompt).
- `tests/test_screening.py` — 9 tests for the scorer: full/partial/no match scoring,
  scorecard ordering, strengths/gaps construction, multi-word + case-insensitive skill
  extraction, rubric weight sums.
- `tests/test_tenant_isolation.py` — **M6 Phase 1**, 6 tests, the first DB-backed
  integration tests in the repo: cross-tenant leak checks for jobs/candidates/interviews,
  same-email-allowed-in-different-tenants, unknown-tenant 404, missing-header-defaults-to-seed.
- `tests/test_rbac.py` — **M6 Phase 2**, 19 parametrized tests: every route class ×
  every role → expected status, plus the unrecognized-email 401 case.
- `tests/test_admin_auth.py` — **new (admin auth module)**, 9 tests: wrong password / unknown
  username → 401, `/admin/*` requires a session (a valid tenant dev-header pair does **not**
  substitute, proving the two auth systems stay isolated), logout invalidates the session,
  full tenant → user (pending → approve → disable) → practice-test lifecycle.
- `tests/test_ai_client_resilience.py` — **new (IA-009)**, 8 tests: a fake `httpx` client double
  drives `llm_client.get_http_client()` so these exercise the real retry/fallback *code paths*
  (`post_with_retry`, `chat_completion`'s fallback logic), not chat_completion mocked away like
  `test_question_generation.py` does. Covers: fallback triggers on both observed failure
  modes (timeout, malformed shape); raises a clear combined error when primary **and** fallback
  both fail; a call with no `fallback_model` configured (every non-cascade caller) fails
  immediately with one attempt, unchanged from before; STT/TTS retry-once-then-succeed and
  retry-then-exhaust.
- `tests/test_candidate_judge.py` — **rewritten (IA-003)**, 8 tests, for the async
  `202`-then-poll flow (was 7 tests / a synchronous `200`/`502` flow before IA-003 backgrounded
  the endpoint). `_poll_until_not_pending` is the test-side equivalent of the frontend's polling
  loop — polls `GET /candidates/{id}` on a short interval until `judgeStatus` leaves `"pending"`,
  deliberately not assuming whether `httpx.ASGITransport` runs `BackgroundTasks` inline or truly
  deferred (empirically it resolves near-instantly: all 8 tests run in 0.64s). Covers: `202` +
  `judgeStatus="pending"` immediately, then polling shows the completed scorecard (rubric's own
  weight, never the LLM's), `scoreMethod == "llm_judge"`, strengths/gaps/aiNote/compareVerdict
  populated; malformed LLM output → `202` then polling shows `judgeStatus="failed"` +
  `judgeError` populated, with the `Application` row's score/scorecard provably untouched (the
  502-on-the-POST version of this test no longer applies — there's no response left to carry a
  synchronous error); a scorecard missing any rubric criterion → same failed-via-polling path;
  **new** — calling `/judge` again while already `judge_status="pending"` → `409` (monkeypatches
  `_run_judge_in_background` to a no-op that never leaves `"pending"`, so the second call has
  something real to collide with); candidate creation never calls the judge at all; judging a job
  with no rubric → `400` synchronously, still pre-background; cross-tenant application id → 404;
  judging then deterministic re-screening the same application flips `scoreMethod` back to
  `"deterministic"` — a documented, tested contract, now polled for completion first.
- `tests/test_interview_sessions.py` — **new (M4), extended (M4b)**, 15 tests: STT/LLM/TTS all monkeypatched at
  `interview_pipeline`'s import site (fake `chat_completion`/`transcribe`/`synthesize`), same
  convention as the other AI-mocked suites — these test the router's persistence/idempotency
  logic, not HTTP-layer resilience (`test_ai_client_resilience.py`'s job). Covers: session
  creation happy path + `400` on non-Voice mode + `400` on zero questions + `404` on an unknown
  interview; a turn call with **no tenant/user headers at all** succeeds (the point of the
  design); a retried `turn_index` returns the cached result without re-running the cascade
  (asserted via a captured-calls counter); a manually-inserted `pending` row for the same
  `(session_id, turn_index)` → `409`; an `LLMError` mid-cascade → row `failed` + `error`
  captured, session stays `active`, and a resubmitted identical `turn_index` succeeds and
  completes; unknown `session_id` → `404`; a turn on an already-`complete` session → `409`;
  history bounding (seeds turns past `interview_history_max_turns`, asserts the captured
  message list sent to the fake LLM stays capped); the `[INTERVIEW_COMPLETE]` sentinel in a
  fake LLM response flips the session to `complete` and is stripped from the returned `aiText`.
  **New (M4b)**: session creation succeeds for `mode="Video"` (previously only `"Voice"` was
  tested — confirms the widened gate); a turn submitted with `audio_format="webm"` on a
  Video-mode session persists `media_type="video"`; a Voice-mode session's turns still persist
  `media_type="audio"` (regression, confirms the default/explicit-set behavior for both paths).
  **Also live-verified against the real OpenRouter API** (not just this mocked suite) — see the
  `interview_sessions.py` callout above for the real TTS-timeout-then-retry finding, and the
  M4b callout below for the real STT-video finding.
- `tests/test_interview_evaluation.py` — **new (M5)**, 10 tests: `chat_completion` monkeypatched
  at `interview_evaluator`'s import site, `evaluate_interview_task.delay` monkeypatched at both
  `interview_sessions.py`'s and `interview_reports.py`'s import sites (never hits a real Redis
  broker in tests). Covers: `evaluate_interview()` directly — successful coercion writes
  score/scorecard/verdict/note + `evaluation_status="complete"`; no `job_id`/rubric →
  `"failed"` with a clear message, not raised; malformed LLM JSON → `"failed"`, not raised.
  Router-level: the `/complete` endpoint sets `evaluation_status="pending"` and calls `.delay()`
  with the right session id; `GET /interviews/{id}/sessions` + `GET .../report` return real data;
  wrong-tenant report access → `404`; `PATCH .../decision` never touches the AI-owned
  score/scorecard fields; `POST .../evaluate`'s `409` guard when already `pending` and `400`
  when the session isn't `complete` yet; the media endpoint's `404` on a null path (turn 0 has
  no candidate audio) and an out-of-range `turn_index`.
- `pytest.ini` — `asyncio_default_fixture_loop_scope = session`, and **every** async test file
  sets `pytest.mark.asyncio(loop_scope="session")` at module level. Needed because the
  module-level async engine in `app/db.py` binds to whichever event loop is running on first
  use; without forcing every file onto the same shared loop, pytest-asyncio's default
  per-test-function loop makes some later DB-touching test reuse connections bound to an
  already-closed loop (`asyncpg.exceptions...: another operation is in progress` / "attached to
  a different loop") — see bug #12 below for the specific way this recurred.

## Real bugs hit (and fixed) — worth remembering

**Voice cascade era:**
1. **`MissingGreenlet` on candidate creation** — assigning a list to an *unloaded*
   SQLAlchemy relationship triggers a lazy-load crash under async. Fixed by re-fetching with
   `selectinload`.
2. **Reasoning leaking into spoken output** — Nemotron sometimes put its thinking in
   `message.content`. Fixed by passing `"reasoning": {"exclude": true}` on interview-brain calls.

**Full-ATS-schema era:**
3. **Alembic autogenerate forgot its own import** — the migration referenced
   `pgvector.sqlalchemy.vector.VECTOR` without importing it. Autogenerate doesn't always add
   imports for custom column types; added by hand.
4. **Autogenerate silently skipped the GIN index** — expression/functional indexes aren't
   detected. Re-added as raw SQL, verified with `\di`.
5. **App and Alembic saw different schemas** — `app/main.py` didn't import every model, so
   `Base.metadata` was missing `users` at runtime. Fixed by centralizing imports in
   `app/models/__init__.py`, imported by both `main.py` and `migrations/env.py`.

**ATS vertical-slice era:**
6. **`ARRAY(String)` rejected by Postgres** — `sqlalchemy.dialects.postgresql.ARRAY(String)`
   isn't a real type; `DatatypeMismatchError` at migration time. Fix: plain `sqlalchemy.ARRAY`.
7. **`async_session` misuse in the seed** — used the sessionmaker's `async_session` attribute
   directly instead of calling it; fixed by instantiating `async_session()`.
8. **The seed data's TypeScript isn't JSON** — `generated-seed.ts` has unquoted keys; the seed
   cleans it up, and the 3 interviews are hardcoded in `app/seed.py` (`SEED_INTERVIEWS`).
9. **View-schema drift** — missing fields (`ResumeOut`, `JobView` import) each surfaced as a
   500 on a different route until schemas were reconciled field-by-field against the frontend types.

**M6 Phase 1/2 era:**
10. **Dead `selectinload(Application.candidate)` on `GET /jobs/{id}/candidates`** — referenced
    an ORM relationship that was never defined on `Application` (only `candidate_id`, no
    `relationship()`). Crashed with `AttributeError` at query-build time on every call — but
    nothing had ever exercised this specific endpoint end-to-end before the new RBAC tests
    (`tests/test_rbac.py`), so it went unnoticed. Fixed by removing the redundant hint: the
    query already selects `Candidate` directly via the join, so eager-loading it again was
    never necessary.
11. **The seed script could never actually re-run past its first success** — `app/seed.py`
    deduped candidates by an in-memory dict populated during that run only, never checking the
    database. A second `python -m app.seed` would try to re-insert every candidate and hit the
    (now-composite) email unique constraint. Fixed with a real `SELECT ... WHERE tenant_id AND
    email` fallback, matching what `Runbook.md`/`CLAUDE.md` already claimed ("idempotent —
    re-runs safely, skips existing emails").

**Admin auth module era:**
12. **`test_health.py` reintroduced the Phase 1 event-loop bug** — it predated the
    `loop_scope="session"` convention (it doesn't touch the DB, so nothing had ever forced the
    fix onto it) and ran its own function-scoped loop. Since pytest collects test files
    alphabetically, it ran *between* `test_admin_auth.py` and `test_rbac.py`, and its
    function-scoped loop poisoned the shared async engine's connections for whatever ran next —
    the exact `asyncpg.exceptions...: another operation is in progress` symptom from the
    original Phase 1 fix, now caused by the one file that never got the marker. All four DB
    files individually passed, and any two together passed — only the full four-file run
    failed, which is what made it non-obvious. Fixed by adding
    `pytestmark = pytest.mark.asyncio(loop_scope="session")` to `test_health.py` too.

**M4-prep / ADR-007 era:**
13. **A raw `httpx.ReadTimeout` propagated completely uncaught, live, on the very first real
    IA-002 measurement run** — the free-tier TTS call in `start_interview` hit the full 60s
    timeout with no `LLMError`, no retry, nothing: an unhandled exception straight out of the
    router. Not a hypothetical — this is what interrupted the first attempt to measure cascade
    latency at all. Fixed by catching `httpx.TimeoutException`/`TransportError` inside the new
    shared `post_with_retry` helper and wrapping them as `LLMError`, which is also what makes
    IA-009's retry/fallback logic reachable — a failure has to become an `LLMError` before
    anything can act on it. A second, related failure on the next run — a 200 response with no
    usable `choices` field — was the exact D1 finding from this project's very first
    architecture review, reproduced live and fixed the same way (see [[AI Architecture]]).

## Known debt (pointers, not restatements)

- Architecture-review findings, current status: [[Project Overview]] → "Architecture review"
  section and `docs/risk-register.md`. `tenant_id`/D3 **resolved** (M6 Phase 1). D1's
  `llm_client.py` half **resolved** (2026-08-10, see bug #13 above) — the orphaned-upload-file
  half is still open. D4 (resume-not-in-prompt) is **half-resolved** — M3's question generation
  personalizes at authoring time; the live cascade prompt is still JD-only, unaddressed because
  M4 hasn't started. The "no git repo" finding no longer applies at all — the repo has real
  commit history now, and R-012/IA-013 fixed the newer "one giant commit" version of the same
  underlying problem (see [[Runbook]] → Version control).
- Two risks found during this session's own architecture review, both since addressed: **R-011**
  (`Interview` could be both shared and personalized at once — fixed via `CHECK
  ck_interviews_no_shared_personalized`) and **R-004** (free-tier interview LLM reliability —
  upgraded from theoretical to observed, then partially mitigated via IA-009's retry/fallback).
- Full structured risk/action lists: `docs/risk-register.md`, `docs/implementation-actions.md`.
- The old `docs/architecture/overview.md` in the repo has been **retired** (pointer only) —
  this note is its successor.
