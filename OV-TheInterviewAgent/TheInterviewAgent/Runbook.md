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
| FastAPI backend | manual process via venv | `uvicorn app.main:app --port 8000 --host 127.0.0.1` |
| React frontend | manual process (Vite) | `npm run dev` (in `frontend/`) |

**Nothing runs as a permanent background service except Postgres.** The frontend and API
need to be running together for the app to be useful — the frontend has no offline mode.

## First-time setup (once per machine)

```bash
cd "/Users/amittiwari/Project/StatnativInterviewApp"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in OPENROUTER_API_KEY (openrouter.ai/keys)
docker compose up -d          # starts Postgres on port 5433
alembic upgrade head          # apply both migrations
python -m app.seed            # load seed data (37 jobs / 228 apps / 90 people / 3 interviews)
cd frontend && npm install    # then come back to repo root
```

## Day-to-day run

```bash
cd "/Users/amittiwari/Project/StatnativInterviewApp"
source venv/bin/activate

docker compose up -d                                  # 1. DB (if not running)
uvicorn app.main:app --port 8000 --host 127.0.0.1     # 2. API → http://localhost:8000/docs
# in a second terminal:
cd frontend && npm run dev                            # 3. UI → http://localhost:5173
```

The Vite dev server proxies `/api` → `127.0.0.1:8000` (config: `frontend/vite.config.ts`).
Set `VITE_API_BASE` in `frontend/.env` to point the app at a different backend.

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
pytest                       # backend tests (screening + health) — from repo root, venv active
cd frontend && npm run build # tsc -b && vite build — the working type gate
cd frontend && npm run lint  # oxlint (may fail: missing darwin-universal binding — pre-existing)
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
