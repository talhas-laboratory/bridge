# Reasoning Bridge

Reasoning Bridge is a small, adapter-first control plane for turning a request
into an inspectable execution plan. It does not require a model provider,
vector store, network service, database, or host application.

The core owns contracts, behavior matching, policy enforcement, deterministic
routing, traces, and execution plans. Hosts provide optional adapters for
classification, context, state, execution, learning, and telemetry.

```python
from reasoning_bridge import BehaviorSpec, BridgeRequest, BridgeRuntime

runtime = BridgeRuntime(
    behaviors=[
        BehaviorSpec(
            behavior_id="implementation",
            priority=80,
            trigger_signals=frozenset({"goal:build"}),
            routing_mode="bias",
            preferred_route="implementation",
        )
    ]
)

result = runtime.plan(
    BridgeRequest(request_id="demo-1", content="Build a small adapter.")
)
print(result.plan.route.route_id)  # implementation
```

Run the dependency-free test suite with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Design constraints

- Python 3.11+ and the standard library only.
- Public records serialize to JSON-compatible dictionaries.
- No adapter calls occur unless explicitly registered and permitted by policy.
- Routing remains deterministic in the absence of optional intelligence.
- Adapter failures are returned as structured warnings rather than hidden fallbacks.

The schema files under `schemas/v1/` are the language-neutral protocol surface.
