---
name: adr
description: Write or update an Architecture Decision Record (ADR) in the project's standard format. Use whenever an architecture-level decision (system boundaries, data model, tech stack, failure handling, scalability, security, deployment) has been made, is being made, or needs to be reconsidered.
---

# ADR skill

Writes Architecture Decision Records to `docs/architecture/decisions/ADR-NNN-short-title.md`,
following the exact template and discipline defined in `.claude/product-architect.md`. This
skill exists so the format is applied consistently, not reinvented per decision.

## Before writing

1. List `docs/architecture/decisions/` and find the highest existing `ADR-NNN` — the new file
   uses the next integer, zero-padded to 3 digits (`ADR-001`, `ADR-002`, ... `ADR-010`, ...).
2. If this decision supersedes an existing ADR, open that file — its `Superseded by:` field
   must be updated to point at the new one, and the new one's `Supersedes:` field points back.
3. Check whether a related product decision exists under `docs/product-decisions/` — if so,
   reference it in `Related product decision:`; if not, don't invent one.
4. Gather real evidence before writing: read the actual code paths, config, schema, or tests
   involved. Per `.claude/product-architect.md`'s evidence discipline — cite concrete paths
   ("Confirmed in `app/services/llm_client.py`"), and mark anything not verified as "Unknown"
   or "Not measured yet" rather than inventing a plausible-sounding number or outcome.

## Template

Use this exact structure — do not add or remove top-level sections:

```markdown
# ADR-NNN: Decision title

- Status: Proposed | Accepted | Superseded | Rejected
- Date: YYYY-MM-DD
- Owners:
- Related product decision:
- Supersedes:
- Superseded by:

## Context

## Decision drivers

## Considered options

### Option 1

### Option 2

### Option 3

## Decision

## Rationale

## Consequences

### Positive

### Negative

### Risks

## Validation plan

## Migration and rollout

## Rollback or exit strategy

## Revisit triggers

## Unresolved questions
```

## Rules
- `Owners:` — never invent a name. Use the actual person who made or owns the decision; if
  genuinely unknown, use `Unassigned`.
- `Considered options` needs at least two real alternatives, not one option plus straw men.
  If an alternative was never seriously considered, say so rather than padding.
- `Consequences` must include real negatives and risks, not just positives — a decision with
  no negatives listed should be treated as suspicious, per the persona's "not agreeable by
  default" stance.
- `Unresolved questions` should not be empty unless the decision is genuinely fully settled —
  most real decisions leave something open; naming it is more useful than omitting it.
- After writing, check whether `docs/risk-register.md` needs a new risk entry (new risks this
  decision introduces) — flag it explicitly if so, don't add it silently without being asked.

## Status field discipline
- `Proposed` — written but not yet acted on.
- `Accepted` — the decision this ADR describes has actually been implemented or is the current
  live approach.
- `Superseded` — a newer ADR replaces this one; keep the file, don't delete it.
- `Rejected` — considered and explicitly not adopted; still worth recording so it isn't
  re-litigated from scratch later.
