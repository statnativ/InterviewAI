# AI Interview Platform (learning project)

MVP vertical slice, built incrementally to learn system design. See the full
milestone roadmap in the plan this was scaffolded from.

Currently implemented: **M0** (skeleton, Postgres, health check) + **M1**
(create a job, create a candidate, upload a resume and have it parsed into
structured JSON via an LLM) + the **full ATS vertical slice** — a React
frontend backed entirely by the FastAPI/Postgres API (no localStorage).

## Architecture

```
React + Vite (frontend/)  ──HTTP /api──►  FastAPI (app/)  ──SQLAlchemy──►  Postgres (docker)
   │                                                                          │
   └── scoring, filters, PDF parse (pdfjs)                                    └── seeded 37 jobs / 228 apps / 3 interviews
```

- The backend owns all state and the screening/scoring logic
  (`app/services/screening.py`, a Python port of the deterministic rubric
  scorer). The browser only renders results.
- The frontend store (`frontend/src/store/useAppStore.ts`) is a thin client
  mirror: `init()` loads everything; every mutation calls the API and syncs
  the returned record(s) back locally.
- Vite proxies `/api` → `127.0.0.1:8000` in dev (see `frontend/vite.config.ts`).

## Setup

```bash
# 1. Start Postgres
docker compose up -d

# 2. Create a venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# then edit .env and set OPENROUTER_API_KEY (https://openrouter.ai/keys)

# 4. Apply database migrations
alembic upgrade head

# 5. Seed the database (idempotent; loads the synthetic ATS data)
python -m app.seed

# 6. Run the API server
uvicorn app.main:app --reload

# 7. (separate terminal) Run the frontend
cd frontend
npm install
npm run dev        # http://localhost:5173 (or 5174 if taken)
```

Open http://localhost:8000/docs for the interactive API (Swagger UI).

## API surface

- `GET/POST /jobs`, `GET/PATCH /jobs/{id}`
- `POST /jobs/{id}/regenerate-rubric` (re-derives rubric from the JD, re-screens everyone)
- `POST /jobs/{id}/save-version` (approves a new version, supersedes the old)
- `GET /jobs/{id}/candidates`
- `GET/POST /candidates`, `GET/PATCH /candidates/{id}` (POST screens + dedupes by email)
- `POST /candidates/{id}/screen`, `POST /candidates/bulk` (shortlist/decision/stage)
- `POST /candidates/{id}/resume` (upload a .pdf/.docx, extracts text, re-screens)
- `GET/POST /interviews`, `GET/PATCH /interviews/{id}`

## Tests

```bash
pytest          # backend unit tests (screening + health)
cd frontend && npx tsc -b && npm run build   # frontend typecheck + production build
```

## Project layout

```
app/
├── main.py          # FastAPI app, mounts routers, CORS
├── config.py        # env-driven settings (pydantic-settings)
├── db.py            # async SQLAlchemy engine/session
├── seed.py          # idempotent seed from frontend/src/data/generated-seed.ts
├── models/          # SQLAlchemy ORM models (Job, Candidate, Application, Resume, Interview, …)
├── schemas/         # Pydantic request/response DTOs (flat view shapes the frontend consumes)
├── routers/         # API endpoints (jobs, candidates, interviews, health)
├── services/        # screening (scoring), LLM client, resume parsing, view mappers
└── storage/         # file storage (local disk for now)

frontend/src/
├── store/useAppStore.ts   # API-backed client mirror of the app state
├── lib/api.ts             # typed fetch client (base: /api)
├── lib/pdf.ts             # pdfjs PDF text extraction for resume upload
└── pages/…                # dashboard, jobs, candidates, interviews, sessions
```
