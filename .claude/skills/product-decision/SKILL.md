---
name: product-decision
description: Write or update a Product Decision record (PD) in the project's standard format. Use whenever a product-level decision has been made — scope, target user, prioritization, success metrics, what to build vs. defer, or what to explicitly exclude.
---

# Product decision skill

Writes product decisions to `docs/product-decisions/PD-NNN-short-title.md`, following the
exact template and discipline defined in `.claude/product-architect.md`. Companion to the
`adr` skill — use this one when the decision is primarily about the customer problem, scope,
or user experience rather than system design.

## Before writing

1. List `docs/product-decisions/` and find the highest existing `PD-NNN` — the new file uses
   the next integer, zero-padded to 3 digits.
2. Check `docs/product/prd.md` and `docs/product/vision.md` first — a product decision should
   be traceable to (or explicitly deviate from) the PRD, not float free of it. If it deviates,
   say so explicitly rather than silently contradicting the PRD.
3. Check `docs/architecture/decisions/` for a related ADR — cross-reference both ways
   (`Related ADRs:` here, `Related product decision:` there) if one exists.
4. Gather real evidence: what was actually stated by the user, what's in the PRD, what's
   inferred vs. genuinely unknown. Per `.claude/product-architect.md`'s evidence discipline —
   do not fabricate user research, adoption data, or success-metric results that don't exist.
   "No user research has been done" is a valid, expected answer for a pre-launch POC.

## Template

Use this exact structure — do not add or remove top-level sections:

```markdown
# PD-NNN: Decision title

- Status:
- Date:
- Owner:
- Related ADRs:

## Customer problem

## Evidence

## Decision

## Alternatives considered

## Scope

## Explicit non-goals

## Success metrics

## Risks

## Validation plan

## Revisit triggers

## Open questions
```

## Rules
- `Evidence` — distinguish clearly between what's actually been observed/stated versus what's
  assumed. A POC with one user (often the builder) has thin evidence by nature; say that
  plainly rather than overstating confidence.
- `Explicit non-goals` is not optional filler — name at least one thing this decision
  deliberately does *not* cover, especially anything the PRD mentions that's being deferred.
- `Success metrics` should reference the PRD's actual stated metrics (§3) where applicable
  rather than inventing new ones, unless this decision genuinely needs a metric the PRD doesn't
  have — in which case say why.
- `Owner:` — never invent a name; use `Unassigned` if genuinely unknown.
- After writing, check whether `docs/implementation-actions.md` needs a new action entry as a
  consequence — flag it explicitly if so.
