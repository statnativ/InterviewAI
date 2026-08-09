---
tags: [project, runbook, how-to]
status: current
last-updated: 2026-08-09
---

# The Interview Agent — Runbook

How to run everything on this machine. Companion to [[Project Overview]] (what the pieces
are) and [[Backend Overview]] (how the code works).

## The stack at a glance

| Piece | Runs as | How to start |
|---|---|---|
| Postgres + pgvector | Docker container (`statnativinterviewapp-postgres-1`) | `docker compose up -d` |
| FastAPI backend | manual process via venv | `uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload` |
| React frontend | manual process (Vite) | `npm run dev` (in `frontend/`) |

**Use `--reload` on uvicorn.** Without it, a backend process started before a code change
(new router, new model, new migration) keeps serving the old code — routes that exist in the
source return `404` until the process is manually killed and restarted. This bit the
admin-auth-module verification pass: the backend had been started in an earlier session before
`app/routers/auth.py`/`admin.py` existed, and `POST /auth/login` 404'd until the process was
restarted. `--reload` avoids this class of stale-process confusion going forward.

**Nothing runs as a permanent background service except Postgres.** The frontend and API
need to be running together for the app to be useful — the frontend has no offline mode.

## First-time setup (once per machine)

```bash
cd "/Users/amittiwari/Project/StatnativInterviewApp"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in OPENROUTER_API_KEY (openrouter.ai/keys)
docker compose up -d          # starts Postgres on port 5433
alembic upgrade head          # apply all four migrations (init, ATS align, tenant isolation, admin auth module)
python -m app.seed            # load seed data (1 tenant, 1 org user, 1 platform admin, 37 jobs / 228 apps / 90 people / 3 interviews)
cd frontend && npm install    # then come back to repo root
```

## Day-to-day run

```bash
cd "/Users/amittiwari/Project/StatnativInterviewApp"
source venv/bin/activate

docker compose up -d                                            # 1. DB (if not running)
uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload      # 2. API → http://localhost:8000/docs
# in a second terminal:
cd frontend && npm run dev                                      # 3. UI → http://localhost:5173
```

The Vite dev server proxies `/api` → `127.0.0.1:8000` (config: `frontend/vite.config.ts`).
Set `VITE_API_BASE` in `frontend/.env` to point the app at a different backend.

**Calling the API directly (curl/Swagger)**: every `jobs`/`candidates`/`interviews` route
requires (or defaults) `X-Tenant-Id` and `X-User-Email` headers — see
[[Identity & Access Overview]] Phase 1/2. Omit both and you get the seed tenant (Northwind
Health) + seed user (Riley Hoffman, recruiter), so `/docs` Swagger calls and plain `curl` still
work unauthenticated-looking, same as before this was added. Pass a real header to see the
tenant-scoping/RBAC behavior, e.g.:
```bash
curl localhost:8000/jobs -H "X-Tenant-Id: 11111111-1111-1111-1111-111111111111"
```

**Master admin login** (`/auth/*`, `/admin/*`) is a separate, real session-cookie auth surface
— see [[Identity & Access Overview]] addendum. No dev headers apply here:
```bash
curl -c cookies.txt -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "statnativ", "password": "<seeded password — see app/seed.py>"}'
curl -b cookies.txt localhost:8000/admin/tenants
```

## Schema changes (migrations)

```bash
alembic upgrade head       # apply pending migrations
alembic revision --autogenerate -m "describe change"
# ALWAYS review the generated file by hand before running it — autogenerate
# has missed imports (pgvector) and whole functional indexes before.
alembic upgrade head
```

## Seeding / resetting data

```bash
python -m app.seed         # idempotent — re-runs safely, skips existing emails/jobs
```

To start from a clean slate (deletes ALL data):
```bash
docker compose down -v && docker compose up -d
alembic upgrade head
python -m app.seed
```

## Checks

```bash
pytest                       # backend tests — 44 total: screening, health, tenant isolation, RBAC, admin auth
                              # (from repo root, venv active; the DB-backed suites hit the real dev DB
                              # and clean up after themselves — see [[Backend Overview]] → Tests)
cd frontend && npm run build # tsc -b && vite build — the working type gate
cd frontend && npm run lint  # oxlint (may fail: missing darwin-universal binding — pre-existing)

# UX regression check (Playwright, real Chromium, screenshots on every check):
cd frontend && node e2e/ux-audit.mjs   # needs backend :8000 + frontend :5173 already running
                                        # output: frontend/e2e/screenshots/ (gitignored, regenerate don't commit)
```

## Docker cheatsheet

```bash
docker compose ps        # is Postgres running
docker compose stop      # stop it (data preserved)
docker compose up -d     # start it again
docker compose down -v   # stop AND delete all data — only for a clean slate

# inspect the DB (extensions, tables, indexes)
docker compose exec postgres psql -U interview -d interview_platform -c '\dx' -c '\dt' -c '\di'
```

Postgres runs on port **5433**, not 5432 (taken by a pre-existing local install). Data lives
in the Docker volume `statnativinterviewapp_pgdata`.

## Standalone demos & scripts

```bash
python scripts/test_interview_pipeline.py   # voice cascade demo (STT→LLM→TTS), writes mp3s to data/pipeline_test/
# synthetic-corpus tooling lives in scripts/synthetic/convert/ (see [[Synthetic Data — Design]])
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker: ... daemon not running` | Start Docker Desktop (`open -a Docker`), wait, retry. |
| Can't connect to Postgres | Check `docker compose ps`; verify port 5433 isn't taken (`lsof -i :5433`). |
| API crashes on a route with a missing-column/type error | The schema and models drifted — run `alembic upgrade head`, or reconcile models + migration (see [[Backend Overview]] bugs 3–6). |
| App shows no data | Backend not running or seed never loaded — run the day-to-day commands + `python -m app.seed`. |
| Frontend can't reach `/api` | Vite proxy needs the backend on 8000; check `frontend/vite.config.ts` and that uvicorn binds 127.0.0.1. |
| `npm run lint` fails on platform binding | Known pre-existing oxlint issue — use `npm run build` as the gate. |
| Adding a candidate gets 409 | Duplicate email (dedupe is case-insensitive) — expected behavior. |
| New DB-backed pytest file fails with `asyncpg... another operation is in progress` / `attached to a different loop` | The module-level async engine (`app/db.py`) binds to whichever event loop is running on first use; pytest-asyncio's default per-test loop breaks that. Add `pytestmark = pytest.mark.asyncio(loop_scope="session")` at the top of **every** async test file in the suite, including ones that don't touch the DB — `pytest.ini` sets the fixture-loop-scope half, but the test-loop-scope half is per-file, and one file missing it (even a DB-free one like `test_health.py`) can poison the shared loop for whatever pytest runs after it alphabetically. See [[Backend Overview]] bug #12 for the exact recurrence of this. |
| `POST /auth/login` (or any `/admin/*` route) returns `404` even though the router exists in the code | The backend process is stale — it was started before that router was added and isn't running with `--reload`. Kill it and restart with `uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload`. |
