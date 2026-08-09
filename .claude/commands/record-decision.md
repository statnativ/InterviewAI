---
description: Record an architecture or product decision as a properly formatted ADR or PD
argument-hint: "<short description of the decision to record>"
---

Decision to record: $ARGUMENTS

Determine whether this is primarily an **architecture** decision (system boundaries, data
ownership, tech stack, failure modes, scalability, etc.) or a **product** decision (customer
problem, scope, success metrics, alternatives from a user/business angle) — per the
distinction in `.claude/product-architect.md`. Many real decisions are both; if so, write an
ADR and a PD and cross-reference them via their `Related ADRs:` / `Related product decision:`
fields, rather than forcing everything into one document.

- For an architecture decision: invoke the `adr` skill.
- For a product decision: invoke the `product-decision` skill.

Before writing, load `.claude/product-architect.md`'s **Evidence discipline** and **Decision
artifacts** sections and follow them exactly — cite concrete repository paths for claims, mark
inferred vs. confirmed vs. unknown explicitly, and never fabricate evidence, owners, or
validation results that don't exist yet. If material context is missing to fill in a required
section honestly, write "Unknown" / "None yet" rather than inventing something plausible.

After writing, check whether `docs/risk-register.md` or `docs/implementation-actions.md` need a
new or updated entry as a consequence of this decision, and say so explicitly if they do.
