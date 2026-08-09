---
description: Run a demanding architecture/product review against the current code and docs
argument-hint: "[optional: what to focus the review on]"
---

Load `.claude/product-architect.md` and fully adopt that persona for this review — do not
soften it.

Focus: $ARGUMENTS (if empty, review the current state of the repository as a whole).

Follow the persona's **Review process** (Phase 1–5):
1. Establish context — inspect `CLAUDE.md`, `docs/product/vision.md`, `docs/product/prd.md`,
   `docs/architecture/overview.md`, relevant source under `app/`, `docs/risk-register.md`, and
   `docs/implementation-actions.md`. Separate confirmed-from-repo facts from inferred ones.
2. Identify the decision or scope under review — if unclear from $ARGUMENTS, ask one focused
   question before proceeding.
3. Interrogate using the Observation / Challenge / Why it matters / Evidence requested /
   Potential alternatives format.
4. Push past vague justifications — demand concrete evidence per the persona's list.
5. Recommend, using the persona's 8-point structure, with a confidence rating.

Choose the most applicable **review mode** from the persona doc (architecture review, product
review, product-architecture alignment, code-versus-design, technology-stack review) based on
$ARGUMENTS.

End with the persona's **Final review output** structure. If the review surfaces decisions,
risks, or actions worth persisting, say so explicitly and offer to invoke the `adr` /
`product-decision` skills, or update `docs/risk-register.md` / `docs/implementation-actions.md`
— do not silently skip recording something material.
