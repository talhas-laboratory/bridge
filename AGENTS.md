# AGENTS.md

Guidance for coding agents working in this repository.

## Modular bridge architecture (required)

Reasoning Bridge is a **multi-function control plane**. Context-packet assembly is
only one optional capability. Whenever you add a feature, change behavior, or
refactor, treat domain functionality as a **modular add-on**, not as something to
fold into the core.

### Core vs extension

| Layer | Owns | Must remain free of |
|---|---|---|
| **Core** (`contracts`, `runtime`, `adapters`, `behaviors`, `routing`, `policy`) | Requests, policy, classification hooks, context retrieval hooks, behavior matching, routing, plans, traces, generic `PlanExtension` hook | Domain-specific packet/recipe/compiler logic, source-system clients, product-specific schemas |
| **Extensions** (`reasoning_bridge.extensions.*`) | Optional domain capabilities | Direct mutation of core control flow except via `PlanExtension` |

The reference extension is `reasoning_bridge.extensions.packet`
(`ContextPacketExtension`). New capabilities should follow that pattern.

### Rules for every change

1. **Do not grow the core to implement a product feature.** Prefer a new
   `PlanExtension` (or a sibling extension package) that attaches named artifacts
   to `ActiveField.extensions`.
2. **Do not import extension modules from core runtime/adapters/contracts.**
   Core may only know the generic `PlanExtension` / `ExtensionContribution`
   protocol.
3. **Keep adapter ports narrow.** Core adapters stay classify / context /
   execute / learn / telemetry. Domain ports (facets, compilers, evaluators,
   etc.) live with their extension.
4. **Preserve opt-in behavior.** Bridge planning must work with zero extensions
   registered. Features activate only when a host passes them via
   `BridgeRuntime(..., extensions=[...])`.
5. **Use named attachments, not new required core fields**, for extension
   outputs. Example: packets use `ActiveField.extensions["context_packet"]`.
6. **Add tests that prove modularity** when introducing an extension:
   - core still plans without the extension
   - core modules do not import the extension package
7. **Document extension entry points** in README or extension docs; do not imply
   the feature is mandatory bridge behavior.
8. **Schemas for extension records** may live under `schemas/v1/`, but label them
   as extension protocol surfaces when relevant.

### When building a new feature, ask

- Can this be a `PlanExtension` or host adapter instead of a core change?
- Does the core still make sense for unrelated bridge functions if this feature
  is absent?
- Am I about to special-case one domain (packets, memory, execution, eval) inside
  `runtime.py`? If yes, stop and extract an extension.

### Allowed core changes

Core changes are appropriate when they improve shared infrastructure used by
many functions, for example:

- richer generic extension hooks
- policy / privacy / budget primitives
- deterministic routing or behavior registry improvements
- serialization, tracing, or adapter-failure contracts

If a change only serves one domain, it belongs in an extension.

## Project constraints

- Python 3.11+, standard library only in shipped package code
- Public records serialize via `to_dict()` to JSON-compatible dictionaries
- Adapter and extension failures become structured warnings, not silent fallbacks
- Prefer small, inspectable modules over broad rewrites

## Verification

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
