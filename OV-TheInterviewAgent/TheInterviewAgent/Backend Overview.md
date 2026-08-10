---
tags: [project, system-design, python, fastapi, backend]
status: current — ATS vertical slice + M6 Phase 1/2 (tenants, RBAC) wired + master admin auth module + M3 (AI question generation) + M4-prep (ADR-007, latency measurement, AI-client retry/fallback) + M2 (LLM-as-judge scoring)
last-updated: 2026-08-10
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
- **Nothing runs as a permanent background service except Postgres** — the API server and
  scripts are started manually ([[Runbook]]).

## Directory map

```
app/
├── main.py            # FastAPI app: CORS, routers, import app.models
├── config.py          # .env → typed settings object (single import point)
├── db.py              # async engine + get_db() dependency
├── deps.py            # get_current_tenant / get_current_user / require_roles (M6 P1/P2)
│                      # + require_platform_admin (master admin session cookie, additive)
├── seed.py            # idempotent seed loader (python -m app.seed) — also seeds the one
│                      # platform admin (statnativ)
├── models/            # SQLAlchemy models (all registered in models/__init__.py)
│                      # + session.py, practice_test.py (master admin module)
├── routers/           # health, jobs, candidates, interviews + auth.py, admin.py
├── schemas/           # Pydantic view schemas — match frontend TS types 1:1
│                      # + auth.py, admin.py schemas
├── services/          # business logic (kept out of the HTTP layer) + authz.py (RBAC matrix)
│                      # + question_generator.py (M3 — LLM question generation)
├── storage/           # local.py — uploaded file storage
migrations/            # Alembic (env.py imports app.models wholesale)
tests/                 # pytest: test_health, test_screening, test_tenant_isolation, test_rbac,
                        # test_admin_auth, test_question_generation, test_ai_client_resilience,
                        # test_candidate_judge
scripts/               # standalone tools (synthetic corpus, voice-cascade demo)
```

## Data model — 13 tables

Full ATS schema, with pgvector embeddings on `resumes`/`skills` and GIN full-text search on
`resumes.raw_text`. Six of the original eleven tables carry `tenant_id` (M6 Phase 1) —
`tenants` itself is the only fully global table; `skills`/`resume_skills`/`job_skills`/
`ai_processing_logs` stay untenanted (shared taxonomy / join tables that inherit isolation
through their parent FKs). Two more tables (`sessions`, `practice_tests`) were added by the
master admin auth module — see the addendum in [[Identity & Access Overview]]:

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
| `applications` | `application.py` | `tenant_id` + the screening record: `candidate_id`+`job_id`+`resume_id`, `status`, `stage`, `match_score`, `match_breakdown` (JSONB, still unused), plus screening outputs **`shortlisted`, `decision`, `pipeline_stage`, `scorecard` (JSONB), `strengths`/`gaps` (string arrays), `compare_verdict`, `ai_note`**, and **`score_method`** (new — `deterministic`/`llm_judge`, `CHECK ck_applications_score_method`, real column + constraint from day one, not inferred — see the LLM-as-judge section below). Fully wired. |
| `interviews` | `interview.py` | `tenant_id` + `title`, `job_title` (plain string, kept as a display fallback), `job_id` (**new, M3** — nullable FK to `jobs`, resolves the [[UX Review]] finding #10 IA gap), `candidate_id` (**new, M3** — nullable FK to `candidates`; set means this interview is personalized for one person, not a shared template), `mode` (Chat/Voice/Avatar), `status` (Draft/Active/Archived), `questions` (JSONB), `duration`, `shared`. **`CHECK ck_interviews_no_shared_personalized`** (new, R-011/IA-012): `shared` and `candidate_id IS NOT NULL` can't both be true — prevents a personalized interview from being broadcast to every applicant. No `scheduled_at` column despite an earlier version of this note claiming otherwise. |
| `ai_processing_logs` | `ai_processing_log.py` | Audit trail for AI calls (model, tokens, cost, success/failure). Table exists, not yet written to. Not tenant-scoped yet — would need it before this becomes a real audit trail (M6 Phase 6). |

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
| `candidates.py` | `GET/POST /candidates` (create = dedupe by email + screen instantly), `GET/PATCH /candidates/{app_id}`, `POST /candidates/{app_id}/screen` (deterministic), `POST /candidates/{app_id}/judge` (**new** — LLM-as-judge, 400 if the job has no rubric, 502 on a bad LLM response), `POST /candidates/bulk`, `POST /candidates/{app_id}/resume` |
| `interviews.py` | `GET/POST /interviews`, `GET/PATCH /interviews/{iv_id}` (**409**, not a raw 500, if a `PATCH` would violate `ck_interviews_no_shared_personalized` — R-011/IA-012), `POST /interviews/{iv_id}/regenerate` (**new, M3** — replaces the whole question set), `POST /interviews/{iv_id}/questions/{q_id}/regenerate` (**new, M3** — replaces one question in place) |
| `auth.py` | **New (admin auth module)**: `POST /auth/login` (username/password → session cookie), `POST /auth/logout`, `GET /auth/me`. Platform-admin only — see [[Identity & Access Overview]] addendum. |
| `admin.py` | **New (admin auth module)**: `GET/POST /admin/tenants`, `GET/POST /admin/users` + `/admin/users/{id}/approve` + `/admin/users/{id}/disable`, `GET/POST /admin/practice-tests`. Every route behind `require_platform_admin` at the router level (`dependencies=[Depends(require_platform_admin)]`). |

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
addendum for why this doesn't count as Phase 3 being done.

## Services — where the logic lives

| Service | Responsibility |
|---|---|
| `authz.py` | **New (M6 Phase 2)**: the RBAC permission matrix as data — `ADMIN`/`RECRUITER`/`HIRING_MANAGER` role constants, `ALL_ROLES`/`WRITE_ROLES` tuples. `app/deps.py`'s `require_roles(*roles)` reads these; routers just declare which tuple a route needs. |
| `screening.py` | **The ATS brain (deterministic)**: `generate_rubric` (draft rubric from a JD, each criterion's description now quoting the actual JD context it matched via `_context_snippet` — was one repeated boilerplate sentence per tag before the [[UX Review]] fix), `derive_score` (weighted coverage vs. rubric), `extract_skills` (against the 163-skill dictionary), `build_strengths`/`build_gaps`, `screen_candidate` (persists scorecard/strengths/gaps/verdict on the application row). Still the free/instant default for candidate creation and résumé upload — untouched by `candidate_judge.py` below. |
| `candidate_judge.py` | **New (M2, LLM-as-judge)**: `judge_candidate` (JD + rubric + a candidate's full structured profile — experience depth, summary, education, certifications, not just `skills` — via one `chat_completion` call, same JSON-mode pattern as `question_generator.py`) reasons per rubric criterion instead of keyword-matching. `_coerce_result` never trusts the raw response: score clamped to `[0,99]`, `weight` always taken from the rubric (never the LLM, guards a hallucinated weight), `shortlisted` computed from the (clamped) score rather than read from the model so it means the same threshold regardless of method, and a scorecard missing any rubric criterion raises `LLMError` rather than persisting an incomplete result. `build_scoring_profile` is a deliberately separate profile builder from `question_generator.build_candidate_profile` (different fields matter for scoring vs. question-writing) and — like that one — omits the candidate's name from the prompt. Explicit, recruiter-triggered, never auto-run on candidate creation. |
| `skill_dictionary.py` | The 163-skill taxonomy, extracted from the frontend's `src/lib/skills.ts` — the source of truth for skill extraction (multi-word priority, case-insensitive). |
| `views.py` | ORM-model → view-schema mappers (`job_to_view`, `candidate_to_view`, `interview_to_view`). |
| `resume_parser.py` | `extract_text` (PDF/DOCX → plain text) — on the ATS upload path. `parse_resume` (LLM → structured JSON) still exists but is **no longer on the ATS path** — screening is deterministic now. |
| `question_generator.py` | **New (M3)**: `generate_questions` (JD + optional candidate profile → 8–12 questions via one `chat_completion` call, same prompt→strip-fences→`json.loads` pattern as `resume_parser.parse_resume`, but raises `LLMError` on bad output instead of falling back), `regenerate_question` (one replacement question, same type/difficulty, avoids duplicating the others), `build_candidate_profile` (compact prompt block from `Candidate`'s already-structured fields — no re-parsing a résumé file). |
| `llm_client.py` | OpenRouter `/chat/completions` via a shared, connection-pooled client (`get_http_client()`, IA-014). Supports `exclude_reasoning=True` to strip a reasoning model's "thinking" from visible output. Response shape validated + a hard-failure retry/fallback (`post_with_retry`, opt-in `fallback_model`) added 2026-08-10 (IA-009) after IA-002 reproduced both failure modes live — depth in [[AI Architecture]]. |
| `stt_client.py` | OpenRouter `/audio/transcriptions`. Model: `qwen/qwen3-asr-flash-2026-02-10`. One same-model retry (IA-009). |
| `tts_client.py` | OpenRouter `/audio/speech`. Model: `hexgrad/kokoro-82m` — **paid**, not free-tier (a prior version of this note miscalled it free-tier). One same-model retry (IA-009) — this is the leg that hit a real 60s timeout during IA-002. |
| `interview_pipeline.py` | Chains STT→LLM→TTS. `start_interview()` + `run_turn()`; conversation history (a list of chat messages) **is** the session state, passed in and returned, not owned by the module. Interviewer brain: `nvidia/nemotron-3-ultra-550b-a55b:free`, with automatic fallback to `deepseek/deepseek-v4-pro` on hard failure (IA-009). Real, live-verified, timed (IA-002: 8.24s/12.51s full-turn totals) — but still a standalone demo, not wired into the app; see ADR-007 for M4's chosen execution model. |

`app/storage/local.py` saves uploaded files under `data/resumes/{candidate_id}/` with a
random prefix.

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
pytest                          # from repo root (venv active) — 69 tests, all DB-backed
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
- `tests/test_candidate_judge.py` — **new (M2, LLM-as-judge)**, 7 tests: a full judge call
  persists a scorecard with one row per rubric criterion (rubric's own weight, never the LLM's),
  `scoreMethod == "llm_judge"`, strengths/gaps/aiNote/compareVerdict populated; malformed LLM
  output → clean 502 with the `Application` row provably untouched; a scorecard missing any
  rubric criterion → 502, not a partial write; candidate creation never calls the judge at all
  (monkeypatched to raise if invoked, not just "happens not to be called"); judging a job with
  no rubric → 400, not 502; cross-tenant application id → 404; judging then deterministic
  re-screening the same application flips `scoreMethod` back to `"deterministic"` — a documented,
  tested contract (the AI score is silently overwritten on re-screen by design, not a bug).
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
