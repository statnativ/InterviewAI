# The Interview Agent (AI Interview Platform) – Claude Code Guide

## What This Project Is
A learning project: system design taught hands-on by building a real AI interview platform
for **Amit Tiwari**. Each milestone ships a working slice of the app; the system-design
concept behind it gets explained when the code actually needs it, not before. Full product
intent lives in [docs/product/prd.md](docs/product/prd.md).

**Living docs live in the Obsidian vault** (`OV-TheInterviewAgent/TheInterviewAgent/`):
[[Project Overview]] (status + roadmap), [[Backend Overview]], [[AI Architecture]],
[[Frontend Overview]], [[Identity & Access Overview]] (M6: tenants/RBAC/SSO/MFA/SCIM),
[[Runbook]], and `ProductResearch/` (market research, UX audit). Keep those current when
behavior changes; decision records stay frozen in `docs/architecture/decisions/`.

## How to Run

```bash
docker compose up -d          # Postgres (pgvector/pgvector:pg16 image)
source venv/bin/activate
alembic upgrade head          # only needed after model changes
python -m app.seed            # idempotent seed (37 jobs / 228 apps / 90 people / 3 interviews / 1 platform admin)
uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload # http://localhost:8000/docs
                               # --reload matters: a process started before a router/model change
                               # keeps serving stale code (404s on new routes) until restarted
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
│   ├── deps.py                        ← get_current_tenant / get_current_user / require_roles
│   │                                    (M6 Phase 1/2 — dev-header identity, real auth in Phase 3)
│   │                                    + require_platform_admin (session cookie, master admin only)
│   ├── models/                       ← 13 tables: tenants, users, candidates, jobs, skills,
│   │                                    resumes, resume_skills, job_skills, applications,
│   │                                    ai_processing_logs, interviews (6 of these carry tenant_id;
│   │                                    interviews also has job_id/candidate_id FKs — M3),
│   │                                    sessions, practice_tests (master admin module)
│   ├── schemas/                      ← Pydantic view DTOs (match frontend TS types 1:1)
│   ├── routers/                       ← health, jobs, candidates, interviews (every route
│   │                                    tenant-scoped + role-checked, see app/deps.py; interviews
│   │                                    also has /regenerate + /questions/{id}/regenerate — M3)
│   │                                    + auth, admin (real session auth, master admin only —
│   │                                    separate surface, doesn't touch the dev-header routes)
│   └── services/                       ← screening (deterministic ATS scoring), authz (RBAC
│                                          permission matrix), views, llm_client, resume_parser,
│                                          question_generator (M3 — AI interview questions),
│                                          stt_client, tts_client, interview_pipeline (OpenRouter)
├── migrations/                          ← Alembic; five migrations (init, ATS align, tenant
│                                            isolation, admin auth module, interview job/candidate links)
├── scripts/test_interview_pipeline.py    ← standalone voice-cascade smoke test
├── tests/                                ← test_health, test_screening, test_tenant_isolation,
│                                            test_rbac, test_admin_auth, test_question_generation
│                                            (53 tests total; the latter four hit the real dev DB)
└── frontend/                              ← React 19 + TS + Tailwind v4 SPA (Vite, port 5173)
    ├── src/lib/api.ts                       ← typed fetch client, proxied /api → :8000, sends
    │                                            X-Tenant-Id / X-User-Email on every call
    ├── src/lib/adminApi.ts                  ← separate client for /admin/*, /auth/* — sends the
    │                                            session cookie (credentials: "include"), never
    │                                            the dev headers above
    ├── src/store/useAppStore.ts             ← Zustand store, API-backed (init() + upsert actions)
    ├── src/pages/                            ← 23 pages across auth/jobs/candidates/interviews/
    │                                            session/avatar — see [[Frontend Overview]]
    ├── src/pages/admin/                       ← AdminLogin, AdminTenants, AdminUsers,
    │                                             AdminPracticeTests (master admin module)
    ├── src/components/                        ← ui/ kit, layout/ shells (incl. AdminShell — the
    │                                              app's first real route guard), candidates/ toolbar
    └── e2e/ux-audit.mjs                        ← Playwright regression script (real Chromium,
                                                    screenshots every check) — node e2e/ux-audit.mjs
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
- **M3 (AI question generation) is shipped** — `NewInterview` calls a real LLM
  (`app/services/question_generator.py`) to draft 8–12 questions from a job description, with
  optional per-candidate personalization; `InterviewEditor` supports editing, drag reorder, and
  regenerating one question or the whole set. `Interview` gained `job_id`/`candidate_id` FKs to
  support this — see [[Project Overview]] and [[Backend Overview]] for detail.
- No *real* auth yet **for tenant users** — M6 Phase 1 (tenant isolation) and Phase 2 (RBAC
  enforcement) are shipped and tested (`X-Tenant-Id`/`X-User-Email` dev headers, `app/deps.py`),
  but there's no login, session, or token for the recruiter/hiring-manager flow. Phase 3 (real
  OIDC SSO) is next — see [[Identity & Access Overview]]. **Separately**, a real email/password
  login now exists for one cross-tenant **master admin** account (`/auth/*`, `/admin/*`,
  session cookie) — it creates tenants, creates/approves/disables tenant users, and authors
  tenant-scoped Practice Tests. It's additive and isolated: it doesn't touch or advance the
  tenant-facing dev-header flow, and Google/SSO login for it was explicitly deferred (no OAuth
  credentials available in that session). Full writeup in [[Identity & Access Overview]]'s
  addendum.
- Local-only dev; nothing is deployed. Cloud target (when we get there) is Cloud Run + Neon —
  see the relevant ADR for the cost reasoning.
- This is an explicit cost-sensitive POC — prefer free/cheap OpenRouter tiers, flag anything
  that would introduce a real recurring bill.
