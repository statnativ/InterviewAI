---
tags: [vault, docs, index]
status: live — doc map current
last-updated: 2026-08-11
---

# The Interview Agent — Vault Home

This vault is the **living documentation** for the AI interview platform project: how it
works, why it works that way, and how to run it. Everything here is updated as the code
changes — stale frontmatter (`status`/`last-updated`) is the tripwire for drift.

## Doc map

| Note | Purpose | Status |
|---|---|---|
| [[Project Overview]] | The big picture: mission, milestone roadmap, mental model, governance layer, what's next | ✅ current (2026-08-11) |
| [[Backend Overview]] | How the backend works: stack, 15-table schema (tenants + tenant_id, sessions, practice_tests, interview job/candidate links, interview evaluation/decision columns), API surface, RBAC, master admin auth, M3 question generation, M4/M4b voice+video cascade, M5 evaluation pipeline (Celery+Redis), services, request traces, tests, bugs | ✅ current (2026-08-11) |
| [[AI Architecture]] | How the AI works: OpenRouter gateway, model choices + costs, each AI service (incl. M5's interview evaluator), deterministic-vs-AI split | ✅ current (2026-08-11) |
| [[Frontend Overview]] | How the React frontend works: API layer, store, pages, the new `/admin/*` module, M3 question-generation UI, M4/M4b voice+video sessions, M5's interview report page, what's real vs. simulated | ✅ current (2026-08-11) |
| [[Synthetic Data — Design]] | The synthetic corpus: 37 jobs / 90 people / 228 applications, pipeline, PDF resumes | ✅ current (2026-08-09) |
| [[Identity & Access Overview]] | M6 plan: tenant isolation → RBAC → OIDC SSO → MFA → SCIM, phased with tests (ADR-005/006); plus an out-of-sequence master admin auth module (email/password, session cookie, cross-tenant) | 🔶 Phase 1 + 2 shipped & tested (2026-08-09); master admin module shipped & tested (2026-08-09); Phase 3 (tenant SSO) next |
| [[Runbook]] | How to run everything: first-time setup, day-to-day commands, migrations, troubleshooting — now includes Redis + the Celery worker (M5) | ✅ current (2026-08-11) |
| [[Enterprise Buyer Research]] | Who buys AI interview/ATS platforms, top buying criteria, compliance (NYC LL 144, EU AI Act), validated pain points | ✅ current (2026-08-09) |
| [[Cost Savings & ROI Model]] | Cost-per-hire/bad-hire benchmarks, an illustrative ROI model built on our own PRD targets, source-credibility tiering | ✅ current (2026-08-09) |
| [[Competitive Landscape]] | Vendor matrix (HireVue, BrightHire, Metaview, Sapia, avatar-led players, etc.), category map, where we're behind table stakes | ✅ current (2026-08-09) |
| [[Enterprise Must-Haves Checklist]] | Concrete must-have features/integrations for enterprise procurement (SSO/SCIM/RBAC, SOC 2, AI-hiring compliance, ATS integrations), checked against our current build | ✅ current (2026-08-09) |
| [[UX Review]] | Live-app UX audit: blank-page deep-link bug, mode/state-sync bugs, accessibility — 6 of 8 findings fixed same session; rubric editor + P2/P3 still open | ✅ current (2026-08-09) |

Engineering artifacts that are **frozen at decision time** (not living docs) live in the
repo, not here: `docs/architecture/decisions/` (ADRs), `docs/product/` (vision, PRD),
`docs/product-decisions/`, `docs/risk-register.md`, `docs/implementation-actions.md`.

## Reading order

- **New to the project** — start here → [[Project Overview]] → [[Runbook]] (first-time setup).
- **New session, picking up work** — [[Project Overview]] (status + "Next up") → the note for
  the layer you're touching (Backend / Frontend / AI) → [[Runbook]].
- **About to change the schema or the AI gateway** — read the ADRs in
  `docs/architecture/decisions/` first; they record why the current choices exist.

## Upkeep rules (what keeps this vault from rotting)

1. **One home per concern.** Explanations live in the vault; decisions live in ADRs;
   requirements in `docs/product/`; risks/actions in the repo registers. A note links to the
   artifact instead of restating it.
2. **Update as you go.** If a session changes behavior, update the affected note(s) in the
   same session — before the work is marked done.
3. **Never copy.** If two notes would contain the same prose, the detail belongs in one place
   and the other links to it.
4. **Frontmatter is the health signal.** Every note carries `status` + `last-updated`; bump
   both on every edit. A `last-updated` more than a few days old means "verify me".
5. **Code is the ultimate reference.** These notes explain and map; when they disagree with
   code, the code wins and the note must be fixed.
