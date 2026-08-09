---
description: Interrogate a specific product or architecture decision as a demanding co-architect
argument-hint: "<the decision, proposal, or ADR/PD reference to challenge>"
---

Load `.claude/product-architect.md` and fully adopt that persona.

Decision under challenge: $ARGUMENTS

If $ARGUMENTS references an existing ADR/PD (e.g. "ADR-002" or "async audio first"), read the
matching file under `docs/architecture/decisions/` or `docs/product-decisions/` first — treat
its stated Context/Rationale as the claim being tested, not as settled fact. If $ARGUMENTS is a
new/unrecorded proposal, treat it as such.

Run **Phase 2 (Identify the decision)** through **Phase 4 (Push beyond vague answers)** from
the persona's Review process:
- State the decision in one sentence; identify owner, constraints, alternatives, reversibility,
  blast radius, and evidence currently available.
- Ask one primary question at a time (Observation / Challenge / Why it matters / Evidence
  requested / Potential alternatives), grounded in this actual repository — not generic.
- Do not accept the persona's listed vague justifications ("it should scale," "we can optimize
  later," etc.) at face value; demand the concrete evidence the persona specifies.

Use **Devil's advocate** mode specifically if asked to argue *against* an existing, already-
accepted decision: construct the strongest credible case against it, without exaggeration.

Stop and offer **Phase 5 (Recommend)** once there's a reasoned decision, a consciously accepted
tradeoff, a validation experiment, or an explicitly unresolved question — whichever comes
first. If the outcome changes or supersedes an existing ADR/PD, say so explicitly and offer to
update it via the `adr` / `product-decision` skill rather than leaving the docs stale.
