# Reasoning Bridge

Reasoning Bridge is a small, adapter-first control plane for turning a request
into an inspectable execution plan. It does not require a model provider,
vector store, network service, database, or host application.

The **core** owns contracts, behavior matching, policy enforcement, deterministic
routing, traces, execution plans, and a generic plan-extension hook. Hosts
provide optional adapters for classification, context, execution, learning, and
telemetry. Domain capabilities such as context-packet assembly are optional
extensions, not core responsibilities.

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

## Extensions

`BridgeRuntime(..., extensions=[...])` accepts modular `PlanExtension`
implementations. Each extension may attach named artifacts onto
`ActiveField.extensions`, plus warnings and trace events. The core never imports
a specific domain extension.

### Context packets (optional)

Packet assembly lives under `reasoning_bridge.extensions.packet` and is enabled
only when you register `ContextPacketExtension`:

```python
from reasoning_bridge import BridgeRequest, BridgeRuntime, ContextPolicy
from reasoning_bridge.extensions.packet import (
    CONTEXT_PACKET_ATTACHMENT,
    ContextPacketExtension,
    PacketRecipe,
    PacketSlotSpec,
)

runtime = BridgeRuntime(
    extensions=[
        ContextPacketExtension(
            recipes=[
                PacketRecipe(
                    recipe_id="implementation_steering",
                    selection_signals=frozenset({"goal:build"}),
                    slots=(
                        PacketSlotSpec("frame", required=True, max_characters=120),
                        PacketSlotSpec("constraints", required=True, max_characters=120),
                    ),
                )
            ]
        )
    ]
)
```

Compiled packets appear at `result.plan.field.extensions[CONTEXT_PACKET_ATTACHMENT]`.

Research grounding for the sparse → rich → over-specified continuum lives in
[`docs/context-packet-research-grounding.md`](docs/context-packet-research-grounding.md).

```bash
PYTHONPATH=src python examples/context_packet.py
```

### Progressive disclosure (optional)

Manifesting + defining forces live under
`reasoning_bridge.extensions.progressive`. Domain meaning is supplied by
swappable `LensVocabulary` packs; operators stay domain-agnostic.

```bash
PYTHONPATH=src python examples/progressive_disclosure.py
```

Attachments:
- `world_manifest`
- `definition_binding`
- `progressive_snapshot`

## Design constraints

- Python 3.11+ and the standard library only.
- Public records serialize to JSON-compatible dictionaries.
- No adapter calls occur unless explicitly registered and permitted by policy.
- Routing remains deterministic in the absence of optional intelligence.
- Adapter and extension failures are returned as structured warnings rather than
  hidden fallbacks.
- Domain features should be extensions; the core stays multi-function.

Agent working rules for preserving this modularity are in
[`AGENTS.md`](AGENTS.md).

## Feature index

An automatic catalog of modules, extensions, schemas, examples, and recent
updates is maintained at:

- [`docs/BRIDGE_INDEX.md`](docs/BRIDGE_INDEX.md)
- [`docs/bridge-index.json`](docs/bridge-index.json)

Regenerate after structural changes:

```bash
python tools/bridge_index.py
```

The schema files under `schemas/v1/` are the language-neutral protocol surface.
