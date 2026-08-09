---
tags: [vault, docs, index]
status: live — doc map current
last-updated: 2026-08-09
---

# The Interview Agent — Vault Home

This vault is the **living documentation** for the AI interview platform project: how it
works, why it works that way, and how to run it. Everything here is updated as the code
changes — stale frontmatter (`status`/`last-updated`) is the tripwire for drift.

## Doc map

| Note | Purpose | Status |
|---|---|---|
| [[Project Overview]] | The big picture: mission, milestone roadmap, mental model, governance layer, what's next | ✅ current (2026-08-09) |
| [[Backend Overview]] | How the backend works: stack, 10-table schema, API surface, services, request traces, tests, bugs | ✅ current (2026-08-09) |
| [[AI Architecture]] | How the AI works: OpenRouter gateway, model choices + costs, each AI service, deterministic-vs-AI split | ✅ current (2026-08-09) |
| [[Frontend Overview]] | How the React frontend works: API layer, store, pages, what's real vs. simulated | ✅ current (2026-08-09) |
| [[Synthetic Data — Design]] | The synthetic corpus: 37 jobs / 90 people / 228 applications, pipeline, PDF resumes | ✅ current (2026-08-09) |
| [[Runbook]] | How to run everything: first-time setup, day-to-day commands, migrations, troubleshooting | ✅ current (2026-08-09) |

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
