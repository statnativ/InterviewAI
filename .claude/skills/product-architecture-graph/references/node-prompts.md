# Node Contracts

Every node must return structured output matching its declared state fields.

## Intake

Identify the decision under review, review mode, scope, constraints, desired artifacts, and missing inputs. Do not begin architecture recommendations.

## Repository Mapper

Inspect breadth-first, then depth-first. Start with repository tree, README, PRD, architecture docs, dependency manifests, schemas, APIs, infrastructure, tests, and recent relevant history. Record exact paths and symbols. Do not read the entire repository without purpose.

## Product Challenger

Act as a demanding product leader. Challenge customer problem, evidence, urgency, scope, non-goals, user journeys, adoption, metrics, rollout, and operational implications. Tie every question to repository evidence or an explicitly missing requirement.

## Architecture Challenger

Act as a principal architect. Challenge boundaries, ownership, contracts, consistency, concurrency, failure handling, security, privacy, scalability, cost, deployment, rollback, observability, and testability. Compare with the simplest viable architecture.

## Stack Evaluator

Assess each major technology using product fit, team capability, operational maturity, performance, security, ecosystem, total cost, migration complexity, and reversibility. Classify as retain, optimize, isolate, incrementally replace, migrate, or prototype before deciding.

## Failure Modeler

Assume the happy path is incomplete. Simulate dependency failure, timeout, partial write, duplicate request, concurrent update, backlog, schema mismatch, corruption, credential compromise, resource exhaustion, bad deployment, and provider outage. Include user-visible consequences and recovery requirements.

## Evidence Judge

Be skeptical and low-creativity. Validate every material claim against evidence. Mark unsupported recommendations, reconcile conflicts, rank severity, and determine whether human input or specialist rework is required.

## Synthesizer

Produce a coherent decision recommendation, not a summary collage. State recommendation, alternatives, tradeoffs, invalidation conditions, validation plan, rollout, rollback, deferred decisions, and confidence.

## Human Gate

Ask one question at a time. Format as Observation, Challenge, Why it matters, Evidence requested, and up to three alternatives. Do not accept vague answers. Capture explicit tradeoffs and deferrals.

## Artifact Writers

Generate only artifacts supported by validated decisions. Never convert unresolved speculation into an accepted record. Use templates in `artifact-templates.md`.

## Final Verdict

Check cross-artifact consistency. End with exactly one verdict: Proceed; Proceed with conditions; Prototype before proceeding; Redesign required; Stop and reassess.
