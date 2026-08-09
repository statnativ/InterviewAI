# The Interview Agent (AI Interview Platform) – Claude Code Guide

## What This Project Is
A learning project: system design taught hands-on by building a real AI interview platform
for **Amit Tiwari**. Each milestone ships a working slice of the app; the system-design
concept behind it gets explained when the code actually needs it, not before. Full product
intent lives in [docs/product/prd.md](docs/product/prd.md).

**Living docs live in the Obsidian vault** (`OV-TheInterviewAgent/TheInterviewAgent/`):
[[Project Overview]] (status + roadmap), [[Backend Overview]], [[AI Architecture]],
[[Frontend Overview]], [[Runbook]]. Keep those current when behavior changes; decision
records stay frozen in `docs/architecture/decisions/`.

## How to Run

```bash
docker compose up -d          # Postgres (pgvector/pgvector:pg16 image)
source venv/bin/activate
alembic upgrade head          # only needed after model changes
python -m app.seed            # idempotent seed (37 jobs / 228 apps / 90 people / 3 interviews)
uvicorn app.main:app --port 8000 --host 127.0.0.1 # http://localhost:8000/docs
# in a second terminal:
cd frontend && npm run dev    # UI → http://localhost:5173 (proxies /api → :8000)

python scripts/test_interview_pipeline.py   # standalone STT->LLM->TTS cascade demo
pytest
```

### First-time setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENROUTER_API_KEY
docker compose up -d
alembic upgrade head
```

## Project Structure
```
StatnativInterviewApp/
├── CLAUDE.md
├── .claude/
│   ├── product-architect.md     ← demanding-principal-architect persona; read before big decisions
│   ├── commands/                 ← /architect-review, /challenge-decision, /record-decision
│   └── skills/                   ← adr, product-decision (auto-write decision records)
├── docs/
│   ├── product/                  ← vision.md, prd.md
│   ├── architecture/             ← decisions/ (ADRs), diagrams/ (overview.md retired → vault)
│   ├── product-decisions/        ← PDs
│   ├── risk-register.md
│   └── implementation-actions.md
├── app/
│   ├── main.py                    ← FastAPI entry point (also registers all models — see below)
│   ├── config.py                   ← pydantic-settings, reads .env
│   ├── db.py                        ← async SQLAlchemy engine/session
│   ├── seed.py                      ← idempotent seed loader (python -m app.seed)
│   ├── models/                       ← 10 tables: users, candidates, jobs, skills, resumes,
│   │                                    resume_skills, job_skills, applications,
│   │                                    ai_processing_logs, interviews
│   ├── schemas/                      ← Pydantic view DTOs (match frontend TS types 1:1)
│   ├── routers/                       ← health, jobs, candidates, interviews
│   └── services/                       ← screening (deterministic ATS scoring), views,
│                                          llm_client, resume_parser, stt_client, tts_client,
│                                          interview_pipeline (OpenRouter for LLM/STT/TTS)
├── migrations/                          ← Alembic; two migrations (init + ATS align)
├── scripts/test_interview_pipeline.py    ← standalone voice-cascade smoke test
└── tests/                                ← test_health.py, test_screening.py
```

## Key Config (`.env`, from `.env.example`)
- `DATABASE_URL` — Postgres, port **5433** (not 5432 — that's taken by a pre-existing local install)
- `OPENROUTER_API_KEY` — single key for every AI call (LLM, STT, TTS), routed by model slug
- `INTERVIEW_LLM_MODEL`, `STT_MODEL`, `TTS_MODEL`, `TTS_VOICE` — see `app/config.py` for current
  model choices and `docs/architecture/decisions/` for why each was picked

## Working with the governance layer
Before a substantial architecture or product decision, load `.claude/product-architect.md` and
follow it — it is a demanding-reviewer persona, not a rubber stamp. It defines the exact
templates for ADRs (`docs/architecture/decisions/ADR-NNN-*.md`) and product decisions
(`docs/product-decisions/PD-NNN-*.md`); use the `adr` / `product-decision` skills or the
`/record-decision` command to write them rather than freehanding the format. Update
`docs/risk-register.md` and `docs/implementation-actions.md` as risks/actions surface — don't
let them go stale.

## Common Tasks
**Add a new milestone feature:** check `docs/implementation-actions.md` and the roadmap table
in `OV-TheInterviewAgent/TheInterviewAgent/Project Overview.md` first — milestones are
sequential on purpose.

**Change the interview LLM/STT/TTS model:** edit the relevant setting in `app/config.py` /
`.env` — every AI call is config-driven by design (see ADR on OpenRouter as gateway).

**Change the DB schema:** edit `app/models/*.py`, then `alembic revision --autogenerate`,
review the generated migration by hand (autogenerate misses extensions, functional indexes,
and sometimes custom-type imports — confirmed twice already), then `alembic upgrade head`.

**Record an architecture or product decision:** use `/record-decision`, or invoke the `adr` /
`product-decision` skill directly.

## Notes
- No auth yet — `jobs.posted_by` and any "current user" concept is a stub for M6.
- Local-only dev; nothing is deployed. Cloud target (when we get there) is Cloud Run + Neon —
  see the relevant ADR for the cost reasoning.
- This is an explicit cost-sensitive POC — prefer free/cheap OpenRouter tiers, flag anything
  that would introduce a real recurring bill.
