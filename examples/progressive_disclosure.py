from reasoning_bridge import BridgeRequest, BridgeRuntime, ContextPolicy
from reasoning_bridge.extensions.progressive import (
    DEFINITION_BINDING_ATTACHMENT,
    WORLD_MANIFEST_ATTACHMENT,
    DefinitionEntry,
    InMemoryDefineProvider,
    InMemoryManifestProvider,
    ProgressiveDisclosureExtension,
    WorldConstituent,
    business_strategy_lens,
)
from reasoning_bridge.extensions.progressive.lenses import LensRegistry


runtime = BridgeRuntime(
    extensions=[
        ProgressiveDisclosureExtension(
            lenses=LensRegistry((business_strategy_lens(),)),
            manifest_provider=InMemoryManifestProvider(
                world_id="acme-q3",
                provenance=("example:strategy-board",),
                constituents=(
                    WorldConstituent("goal-1", "goal", "Activate design partners", salience=0.95, requires_definition=True),
                    WorldConstituent("segment-1", "customer_segment", "EU prosumer creators", salience=0.9, requires_definition=True),
                    WorldConstituent("budget-1", "budget", "Campaign budget", salience=0.88, requires_definition=True),
                    WorldConstituent("capacity-1", "capacity", "GTM team capacity", salience=0.7),
                    WorldConstituent("competitor-1", "competitor", "Incumbent suite vendor", salience=0.55),
                ),
            ),
            define_provider=InMemoryDefineProvider(
                (
                    DefinitionEntry("goal-1", "Activate 200 design partners by Nov 1.", "locked", "okrs.md"),
                    DefinitionEntry("segment-1", "EU prosumer creators with existing audience >5k.", "locked", "gtm.md"),
                    DefinitionEntry("budget-1", "Hard cap €40k this cycle.", "locked", "finance.md"),
                    DefinitionEntry("capacity-1", "One GTM pod, no extra headcount.", "preferred", "staffing.md"),
                )
            ),
            max_definitions=3,
        )
    ]
)

result = runtime.plan(
    BridgeRequest(
        request_id="strategy-1",
        content="Choose the Q3 GTM budget focus for our EU segment.",
        signals=frozenset({"domain:business", "goal:strategy"}),
        policy=ContextPolicy(allow_context=True),
        metadata={"lens_id": "business_strategy"},
    )
)

manifest = result.plan.field.extensions[WORLD_MANIFEST_ATTACHMENT]
binding = result.plan.field.extensions[DEFINITION_BINDING_ATTACHMENT]
print(
    {
        "lens": manifest.lens_id,
        "manifested": [item.constituent_id for item in manifest.constituents],
        "defined": [item.constituent_id for item in binding.definitions],
        "deferred": list(binding.deferred),
        "definitions": {item.constituent_id: item.claim for item in binding.definitions},
    }
)
