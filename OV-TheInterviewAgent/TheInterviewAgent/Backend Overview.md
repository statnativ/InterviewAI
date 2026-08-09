---
tags: [project, system-design, python, fastapi, backend]
status: current — full ATS vertical slice wired
last-updated: 2026-08-09
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
├── seed.py            # idempotent seed loader (python -m app.seed)
├── models/            # SQLAlchemy models (all registered in models/__init__.py)
├── routers/           # health, jobs, candidates, interviews
├── schemas/           # Pydantic view schemas — match frontend TS types 1:1
├── services/          # business logic (kept out of the HTTP layer)
├── storage/           # local.py — uploaded file storage
migrations/            # Alembic (env.py imports app.models wholesale)
tests/                 # pytest: test_health, test_screening
scripts/               # standalone tools (synthetic corpus, voice-cascade demo)
```

## Data model — 10 tables

Full ATS schema, with pgvector embeddings on `resumes`/`skills` and GIN full-text search on
`resumes.raw_text`:

| Table | Model file | Purpose |
|---|---|---|
| `users` | `user.py` | `email`, `name`, `role` (admin/recruiter/hiring_manager). No auth yet; gives `jobs.posted_by` a target. |
| `jobs` | `job.py` | The JD: `description`, `department`, `requirements`, `location`, `employment_type`, `experience_level`, `salary_min/max`, `currency`, `status`, `posted_by`, plus **`rubric` (JSONB)** and **`versions` (JSONB)** — the frontend contract. |
| `candidates` | `candidate.py` | Full ATS profile: identity (`name`, `email` UNIQUE, `phone`, `location`, `linkedin_url`, `portfolio_url`), sourcing (`source`, `tags`, `notes`), and the extracted resume (`resume_file`, `years_exp`, `current_title`, `current_company`, `skills`, `summary`, `experience`, `education`, `certifications` — JSONB). |
| `resumes` | `resume.py` | `file_path`, `raw_text`, `parsed_data` (JSONB), `embedding` (`Vector(1536)`), `ai_summary`, `ai_strengths`/`ai_concerns`, `years_experience`, `seniority_level`, `is_primary`. Indexes: ivfflat (embedding), GIN (raw_text), partial `(candidate_id, is_primary)`. |
| `skills` | `skill.py` | Taxonomy: `name`, `category`, `aliases` (array), `embedding`. ivfflat index. Not wired to endpoints yet. |
| `resume_skills`, `job_skills` | `resume_skill.py`, `job_skill.py` | Many-to-many joins (composite PKs, no surrogate id). Not wired to endpoints yet. |
| `applications` | `application.py` | The screening record: `candidate_id`+`job_id`+`resume_id`, `status`, `stage`, `match_score`, `match_breakdown` (JSONB), plus screening outputs **`shortlisted`, `decision`, `pipeline_stage`, `scorecard` (JSONB), `strengths`/`gaps` (string arrays), `compare_verdict`, `ai_note`**. Fully wired. |
| `interviews` | `interview.py` | `job_id`, `candidate_id`, `status`, `scheduled_at`, **`questions` (JSONB)**. Added in migration `a1b2c3d4e5f6` — this closed the review's D2 gap. |
| `ai_processing_logs` | `ai_processing_log.py` | Audit trail for AI calls (model, tokens, cost, success/failure). Table exists, not yet written to. |

### Schema evolution (the migration story)

- `68b7d2e3a988_init_full_schema.py` — replaced the original 3-table migration: both
  extensions + all 9 original tables/indexes (columns were renamed/added-as-NOT-NULL, so
  layering on top wasn't possible).
- `a1b2c3d4e5f6_align_schema_for_ats.py` — aligned the schema to the frontend contract:
  job rubric/versions, candidate profile columns, application screening columns,
  `interviews` table.
- `migrations/env.py` does `import app.models` so Alembic and the app can never see
  different slices of the schema (see the bug below that caused this).

> One deliberate deviation from the original SQL: no explicit `idx_candidates_email` —
> `email` is UNIQUE, which Postgres indexes automatically.

## API surface

Full reference lives in Swagger at `http://localhost:8000/docs` (auto-generated from
`app/schemas/`). The map:

| Router | Endpoints |
|---|---|
| `health.py` | `GET /health` |
| `jobs.py` | `GET/POST /jobs`, `GET/PATCH /jobs/{job_id}`, `POST /jobs/{job_id}/regenerate-rubric`, `POST /jobs/{job_id}/save-version`, `GET /jobs/{job_id}/candidates` |
| `candidates.py` | `GET/POST /candidates` (create = dedupe by email + screen instantly), `GET/PATCH /candidates/{app_id}`, `POST /candidates/{app_id}/screen`, `POST /candidates/bulk`, `POST /candidates/{app_id}/resume` |
| `interviews.py` | `GET/POST /interviews`, `GET/PATCH /interviews/{iv_id}` |

Design rules: view schemas are flat and match `frontend/src/data/types.ts` field-for-field
(`app/services/views.py` maps ORM → view); business logic never lives in routers — it's in
`app/services/`.

## Services — where the logic lives

| Service | Responsibility |
|---|---|
| `screening.py` | **The ATS brain (deterministic)**: `generate_rubric` (draft 4-criteria rubric from a JD), `derive_score` (weighted coverage vs. rubric), `extract_skills` (against the 163-skill dictionary), `build_strengths`/`build_gaps`, `screen_candidate` (persists scorecard/strengths/gaps/verdict on the application row). |
| `skill_dictionary.py` | The 163-skill taxonomy, extracted from the frontend's `src/lib/skills.ts` — the source of truth for skill extraction (multi-word priority, case-insensitive). |
| `views.py` | ORM-model → view-schema mappers (`job_to_view`, `candidate_to_view`, `interview_to_view`). |
| `resume_parser.py` | `extract_text` (PDF/DOCX → plain text) — on the ATS upload path. `parse_resume` (LLM → structured JSON) still exists but is **no longer on the ATS path** — screening is deterministic now. |
| `llm_client.py` | OpenRouter `/chat/completions`. Supports `exclude_reasoning=True` to strip a reasoning model's "thinking" from visible output. |
| `stt_client.py` | OpenRouter `/audio/transcriptions`. Model: `qwen/qwen3-asr-flash-2026-02-10`. |
| `tts_client.py` | OpenRouter `/audio/speech`. Model: `hexgrad/kokoro-82m`. |
| `interview_pipeline.py` | Chains STT→LLM→TTS. `start_interview()` + `run_turn()`; conversation history (a list of chat messages) **is** the session state. Interviewer brain: `nvidia/nemotron-3-ultra-550b-a55b:free`. Standalone demo only (M4 not wired into the app). |

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
pytest                          # from repo root (venv active)
```

- `tests/test_health.py` — liveness endpoint.
- `tests/test_screening.py` — 9 tests for the scorer: full/partial/no match scoring,
  scorecard ordering, strengths/gaps construction, multi-word + case-insensitive skill
  extraction, rubric weight sums. (10 total with `test_health.py`.)

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

## Known debt (pointers, not restatements)

- Architecture-review findings still open (LLM error handling, orphaned upload files, no git
  repo, no `tenant_id`, resume-not-in-prompt): [[Project Overview]] → "Architecture review"
  section and `docs/risk-register.md`.
- Full structured risk/action lists: `docs/risk-register.md`, `docs/implementation-actions.md`.
- The old `docs/architecture/overview.md` in the repo has been **retired** (pointer only) —
  this note is its successor.
