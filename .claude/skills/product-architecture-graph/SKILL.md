---
name: product-architecture-graph
description: Orchestrate a graph-based, multi-model product and architecture review of a codebase, PRD, product vision, or technical proposal. Use when the user wants a demanding principal-architect review, product challenge, technology-stack evaluation, failure-mode analysis, human-in-the-loop decision process, ADRs, product decision records, diagrams, risk registers, or implementation actions. The workflow branches specialist reviews in parallel, merges evidence, loops on unresolved decisions, and produces decision artifacts grounded in repository evidence.
---

# Product Architecture Graph

Use this skill as a control plane for a state-machine workflow. Do not collapse the workflow into one monolithic prompt.

## Required resources

Read these files before execution:

- `references/graph.yaml` for nodes, edges, routing, loops, and model roles.
- `references/state-schema.md` for shared state and evidence rules.
- `references/node-prompts.md` for node-specific responsibilities and outputs.
- `references/artifact-templates.md` when generating ADRs, product decisions, risks, diagrams, or actions.
- `references/runtime-guide.md` when implementing the graph in an orchestration framework.

## Operating rules

1. Inspect the repository from the current working directory. Treat documentation as intended behavior and code as implemented behavior.
2. Route work through the graph in `references/graph.yaml`.
3. Assign each node to the configured model role. Permit different providers or models per node.
4. Keep all findings in shared state. Attach repository paths, symbols, configuration values, or user statements as evidence.
5. Never present inference as fact. Mark each claim as `confirmed`, `stated`, `inferred`, or `unknown`.
6. Run independent specialist nodes in parallel when the runtime permits.
7. Merge specialist outputs only through the evidence judge and synthesis nodes.
8. Pause at human-review nodes when a consequential decision, destructive change, migration, or unresolved requirement requires user input.
9. Loop only on unresolved high-severity decisions. Stop when resolved, explicitly deferred, or the configured review-round limit is reached.
10. Challenge both underengineering and overengineering. Always compare against the simplest architecture that satisfies current requirements.
11. Do not recommend a stack migration without measurable benefits, migration phases, rollback, success criteria, and abort criteria.
12. Do not modify production code during review mode. Produce proposed artifacts and actions first.

## Default execution

1. Run `intake`.
2. Run `repository_mapper`.
3. Fan out to `product_challenger`, `architecture_challenger`, `stack_evaluator`, and `failure_modeler`.
4. Run `evidence_judge` to reject unsupported claims and reconcile conflicts.
5. Run `synthesizer` to create a decision-focused assessment.
6. Route to `human_gate` when critical questions remain.
7. Loop to the relevant specialist node for answers or additional evidence.
8. When decisions are sufficient, fan out to `adr_writer`, `product_decision_writer`, `diagrammer`, `risk_register_writer`, and `action_planner`.
9. Run `final_verdict` and end with one verdict: `Proceed`, `Proceed with conditions`, `Prototype before proceeding`, `Redesign required`, or `Stop and reassess`.

## Model policy

Use model roles, not hard-coded providers:

- `fast_mapper`: inexpensive, long-context model for repository inventory and extraction.
- `product_reasoner`: strong product reasoning model.
- `architecture_reasoner`: strongest available systems-design and code reasoning model.
- `adversarial_reasoner`: independent model family when possible, used to challenge consensus.
- `evidence_judge`: precise model with low creativity and strong citation discipline.
- `artifact_writer`: reliable structured-output model.

Prefer model diversity for independent review branches. Do not let the same model produce and judge the same claim when an alternative is available.

## Invocation examples

- "Review this repository as a demanding principal architect. Use the full graph and stop at the human gate before writing ADRs."
- "Run a technology-stack review. Compare retain, optimize, isolate, incrementally replace, migrate, and prototype-before-deciding options."
- "Compare the PRD with the implementation, identify mismatches, and create ADRs, product decisions, diagrams, risks, and implementation actions."

## Validation

Before packaging or changing the graph, run:

```bash
python scripts/validate_graph.py references/graph.yaml
```
