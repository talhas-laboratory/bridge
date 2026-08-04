# Bridge Index

Automatically generated catalog of Reasoning Bridge modules, extensions,
schemas, examples, and recent updates.

- Generated at: `2026-08-04T23:08:25.284105+00:00`
- Package version: `0.1.0`
- Known extensions: `packet`, `progressive`

Regenerate with:

```bash
python tools/bridge_index.py
```

## Category map

| Category | Entries |
|---|---|
| `core` | 7 |
| `extension_hook` | 1 |
| `extension` | 11 |
| `schema` | 7 |
| `example` | 3 |
| `docs` | 2 |
| `tooling` | 1 |

## Modules

### core

| Module | Layer | Summary | Tags | Last update |
|---|---|---|---|---|
| `reasoning_bridge` | `core` | A lightweight, adapter-first reasoning control plane. | core | `594878134ef6` refactor: make context packets an optional plan extension |
| ↳ exports | | `ActiveField`, `AdapterRegistry`, `BehaviorRegistry`, `BehaviorSpec`, `BridgeRequest`, `BridgeResult`, `BridgeRuntime`, `Classification`, `ContextItem`, `ContextPolicy`, `ExecutionPlan`, `ExtensionContribution`, … | | |
| `reasoning_bridge.adapters` | `core` | Narrow adapter protocols and dependency-free reference adapters. | adapter-port, core, registry | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.behaviors` | `core` | Data-backed behavior registration and deterministic matching. | core, registry | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `reasoning_bridge.contracts` | `core` | Versioned, JSON-compatible records exposed by the bridge core. | contract, core, policy | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.policy` | `core` | Policy normalization and capability-safe defaults. | core, policy | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `reasoning_bridge.routing` | `core` | Deterministic route selection from activated behaviors. | core | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `reasoning_bridge.runtime` | `core` | Small orchestration runtime with explicit, policy-gated adapter calls. | core, runtime | `594878134ef6` refactor: make context packets an optional plan extension |

### extension_hook

| Module | Layer | Summary | Tags | Last update |
|---|---|---|---|---|
| `reasoning_bridge.extensions` | `extensions` | Optional plan-time extension hooks for the bridge core. | extension, hook, plan-extension | `594878134ef6` refactor: make context packets an optional plan extension |
| ↳ exports | | `ExtensionContribution`, `PlanExtension` | | |

### extension

| Module | Layer | Summary | Tags | Last update |
|---|---|---|---|---|
| `reasoning_bridge.extensions.packet` | `extension:packet` | Context-packet assembly as an optional bridge extension. | extension, packet | `594878134ef6` refactor: make context packets an optional plan extension |
| ↳ exports | | `CONTEXT_PACKET_ATTACHMENT`, `ContextPacket`, `ContextPacketExtension`, `DefaultPacketCompiler`, `DensityReport`, `FacetMaterial`, `FacetProviderPort`, `InMemoryFacetProvider`, `PacketCompilerPort`, `PacketRecipe`, `PacketSection`, `PacketSlotSpec`, … | | |
| `reasoning_bridge.extensions.packet.adapters` | `extension:packet` | Adapter ports owned by the optional context-packet extension. | adapter-port, extension, packet | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.extensions.packet.compiler` | `extension:packet` | Declarative context-packet recipes and a deterministic default compiler. | extension, packet, recipe, registry | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.extensions.packet.contracts` | `extension:packet` | Contracts owned by the optional context-packet extension. | contract, extension, packet, recipe | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.extensions.packet.extension` | `extension:packet` | Plan-time extension that compiles context packets without coupling the core. | extension, packet, plan-extension | `594878134ef6` refactor: make context packets an optional plan extension |
| `reasoning_bridge.extensions.progressive` | `extension:progressive` | Progressive disclosure: manifesting + defining forces with lens vocabularies. | extension, progressive | — |
| ↳ exports | | `DEFINITION_BINDING_ATTACHMENT`, `PROGRESSIVE_SNAPSHOT_ATTACHMENT`, `WORLD_MANIFEST_ATTACHMENT`, `ConstituentKindSpec`, `DefinePort`, `DefinitionBinding`, `DefinitionEntry`, `InMemoryDefineProvider`, `InMemoryManifestProvider`, `LensRegistry`, `LensVocabulary`, `ManifestPort`, … | | |
| `reasoning_bridge.extensions.progressive.adapters` | `extension:progressive` | Ports for the manifesting and defining forces. | adapter-port, extension, progressive | — |
| `reasoning_bridge.extensions.progressive.contracts` | `extension:progressive` | Domain-agnostic progressive disclosure contracts. Manifesting force = which constituents are in play. Defining force = s… | contract, extension, progressive | — |
| `reasoning_bridge.extensions.progressive.engine` | `extension:progressive` | Deterministic progressive disclosure engine: manifest → select → define → defer. | extension, progressive | — |
| `reasoning_bridge.extensions.progressive.extension` | `extension:progressive` | Plan-time progressive disclosure extension with swappable lens vocabularies. | extension, plan-extension, progressive | — |
| `reasoning_bridge.extensions.progressive.lenses` | `extension:progressive` | Lens vocabulary registry and starter domain packs. Lenses populate kind vocabularies only. Retrieval/providers stay sepa… | extension, progressive, registry | — |

## Assets

| Asset | Category | Summary | Related | Last update |
|---|---|---|---|---|
| `schema:behavior-spec.schema` | `schema/core` | BehaviorSpec | `reasoning_bridge.contracts` | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `schema:bridge-request.schema` | `schema/core` | BridgeRequest | `reasoning_bridge.contracts` | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `schema:context-packet.schema` | `schema/extension:packet` | ContextPacket | `reasoning_bridge.extensions.packet` | `2db0f5f1636a` feat: add configurable context-packet infrastructure |
| `schema:definition-binding.schema` | `schema/extension:progressive` | DefinitionBinding | `reasoning_bridge.extensions.progressive` | — |
| `schema:lens-vocabulary.schema` | `schema/extension:progressive` | LensVocabulary | `reasoning_bridge.extensions.progressive` | — |
| `schema:packet-recipe.schema` | `schema/extension:packet` | PacketRecipe | `reasoning_bridge.extensions.packet` | `2db0f5f1636a` feat: add configurable context-packet infrastructure |
| `schema:world-manifest.schema` | `schema/extension:progressive` | WorldManifest | `reasoning_bridge.extensions.progressive` | — |
| `example:context_packet` | `example/extension:packet` | Example script `context_packet.py` | — | `594878134ef6` refactor: make context packets an optional plan extension |
| `example:custom_adapter` | `example/core` | Example script `custom_adapter.py` | — | `54e94b9a95b5` feat: add adapter-first reasoning bridge core |
| `example:progressive_disclosure` | `example/extension:progressive` | Example script `progressive_disclosure.py` | — | — |
| `docs:context-packet-research-grounding` | `docs/extension:packet` | Context Packet Research Grounding | — | `594878134ef6` refactor: make context packets an optional plan extension |
| `tool:bridge_index` | `tooling/index` | Automatic bridge module/feature indexer. Scans the repository, categorizes core vs extension surfaces, and writes: - docs/bridge-index.json (machine-readable) - docs/BRIDGE_INDEX.md (human-readable) Stdlib only. Safe to run without network. Prefer regenerating after any feature, extension, schema, or example change. | — | `3e9f94a4f81e` feat: add automatic bridge module and feature index |
| `docs:AGENTS` | `docs/agent-guidance` | Agent working rules for modular bridge development | `reasoning_bridge.extensions` | `3e9f94a4f81e` feat: add automatic bridge module and feature index |

## Recent repository updates

| Commit | Date | Subject |
|---|---|---|
| `3e9f94a` | 2026-08-04T13:00:53+00:00 | feat: add automatic bridge module and feature index |
| `b863190` | 2026-08-04T12:51:38+00:00 | docs: add AGENTS.md modularity rules for bridge work |
| `5948781` | 2026-08-04T12:50:00+00:00 | refactor: make context packets an optional plan extension |
| `5de3c19` | 2026-08-04T12:46:06+00:00 | docs: add research grounding for context-packet design |
| `2db0f5f` | 2026-08-04T12:36:19+00:00 | feat: add configurable context-packet infrastructure |
| `5dbeda4` | 2026-07-23T18:30:01+02:00 | chore: ignore generated Python artifacts |
| `54e94b9` | 2026-07-23T18:29:49+02:00 | feat: add adapter-first reasoning bridge core |

## How agents should use this

1. Check this index before adding a feature to see whether a module/extension already covers it.
2. Place new domain capabilities under `src/reasoning_bridge/extensions/<name>/`.
3. Regenerate the index after adding/changing modules, schemas, examples, or docs.
4. Keep core entries free of domain-specific packet/memory/eval logic.
