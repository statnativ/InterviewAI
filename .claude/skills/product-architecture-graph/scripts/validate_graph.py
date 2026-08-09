#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_graph.py <graph.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = yaml.safe_load(path.read_text())
    nodes = data.get("nodes", {})
    errors = []
    entry = data.get("entrypoint")
    if entry not in nodes:
        errors.append(f"entrypoint '{entry}' does not exist")
    roles = set(data.get("model_roles", {}))
    for name, node in nodes.items():
        role = node.get("model_role")
        if role and role not in roles:
            errors.append(f"node '{name}' uses unknown model_role '{role}'")
        nxt = node.get("next")
        if nxt and nxt not in nodes:
            errors.append(f"node '{name}' points to missing next node '{nxt}'")
        for branch in node.get("branches", []):
            if branch not in nodes:
                errors.append(f"node '{name}' has missing branch '{branch}'")
        join = node.get("join")
        if join and join not in nodes:
            errors.append(f"node '{name}' has missing join '{join}'")
        routes = node.get("routes", [])
        if isinstance(routes, list):
            targets = [r.get("to") for r in routes]
        elif isinstance(routes, dict):
            targets = list(routes.values())
        else:
            errors.append(f"node '{name}' routes must be a list or mapping")
            targets = []
        for target in targets:
            if target and target not in nodes:
                errors.append(f"node '{name}' routes to missing node '{target}'")
        then = node.get("then")
        if then and then not in nodes:
            errors.append(f"node '{name}' has missing then node '{then}'")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Graph valid: {len(nodes)} nodes, {len(roles)} model roles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
