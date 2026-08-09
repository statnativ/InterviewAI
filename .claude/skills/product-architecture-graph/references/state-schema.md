# Shared State Schema

Use one durable state object for the graph. Nodes may append to owned fields but must not silently overwrite another node's evidence.

## Core fields

```yaml
run_id: string
review_mode: string
review_round: integer
decision_under_review: string
constraints: []
unknowns: []
repository_map: []
current_stack: []
current_architecture: []
evidence_index: []
product_findings: []
architecture_findings: []
stack_assessment: []
failure_scenarios: []
validated_findings: []
rejected_claims: []
conflicts: []
unresolved_decisions: []
required_decisions: []
human_answers: []
accepted_tradeoffs: []
deferred_decisions: []
recommendations: []
experiments: []
adrs: []
product_decisions: []
diagrams: []
risk_register: []
implementation_actions: []
final_verdict: string
```

## Evidence object

```yaml
id: E-001
claim: string
status: confirmed | stated | inferred | unknown
source_type: code | documentation | configuration | test | git | user | benchmark
source: path, symbol, commit, command output, or user statement
excerpt_or_summary: string
confidence: high | medium | low
collected_by: node name
```

## Finding object

```yaml
id: F-001
domain: product | architecture | stack | failure | security | operations
statement: string
severity: critical | high | medium | low
supporting_evidence: [E-001]
contradicting_evidence: []
assumptions: []
recommended_action: string
owner: Unassigned
status: open | accepted | rejected | deferred | resolved
```

## Merge rules

- Deduplicate findings by underlying decision or failure, not wording.
- Preserve disagreements as explicit conflicts.
- Reject claims with no evidence unless clearly labeled as hypotheses.
- Escalate to human review when a critical finding depends on an unstated requirement.
- Never invent owners, deadlines, benchmarks, load, or compliance requirements.
