# Runtime Guide

This skill defines orchestration semantics; it does not itself create parallel model processes. Implement `graph.yaml` in a runtime that supports durable state, conditional edges, parallel branches, and human interrupts.

## Adapter contract

Each model adapter should expose:

```python
invoke(model_role, node_name, prompt, state_subset, tools) -> NodeResult
```

`NodeResult` must contain:

```yaml
state_updates: {}
evidence: []
route: optional string
messages: []
```

## Execution semantics

1. Load `graph.yaml` and initialize state.
2. Resolve each `model_role` to a provider/model in runtime configuration.
3. Execute ordinary nodes sequentially.
4. Execute `parallel` branches concurrently and merge only at their declared join node.
5. Persist state after every node.
6. Suspend execution at `human_review` nodes and resume with the human answer added to state.
7. Enforce `max_review_rounds`.
8. Log model, prompt version, token usage, latency, and state changes for every node.

## Example model mapping

```yaml
models:
  fast_mapper: provider/model-a
  product_reasoner: provider/model-b
  architecture_reasoner: provider/model-c
  adversarial_reasoner: provider/model-d
  evidence_judge: provider/model-e
  artifact_writer: provider/model-a
```

Use different model families for `architecture_reasoner` and `adversarial_reasoner` when practical.

## Claude Code use

Claude Code can host the repository-facing workflow, but true multi-model execution requires an external orchestrator, agent SDK, MCP server, or command that invokes the selected providers. Keep repository access local and pass only the minimum relevant context to each model node.
