from reasoning_bridge import (
    AdapterRegistry,
    BehaviorSpec,
    BridgeRequest,
    BridgeRuntime,
    ContextPolicy,
)
from reasoning_bridge.extensions.packet import (
    CONTEXT_PACKET_ATTACHMENT,
    ContextPacketExtension,
    FacetMaterial,
    InMemoryFacetProvider,
    PacketRecipe,
    PacketSlotSpec,
    SourceBinding,
)


runtime = BridgeRuntime(
    behaviors=[
        BehaviorSpec(
            behavior_id="implementation",
            priority=80,
            trigger_signals=frozenset({"goal:build"}),
            routing_mode="bias",
            preferred_route="implementation",
            directives=("produce_a_small_next_slice",),
        )
    ],
    extensions=[
        ContextPacketExtension(
            recipes=[
                PacketRecipe(
                    recipe_id="implementation_steering",
                    priority=50,
                    activation_goal="implementation_agent",
                    selection_signals=frozenset({"goal:build"}),
                    density_profile="balanced",
                    max_characters=500,
                    anti_caricature_rules=("prefer realistic competence over caricature",),
                    slots=(
                        PacketSlotSpec("frame", required=True, max_characters=140),
                        PacketSlotSpec("constraints", required=True, max_characters=140),
                        PacketSlotSpec("evidence", required=False, max_characters=180),
                        PacketSlotSpec("open_vars", required=False, max_characters=80),
                    ),
                    source_bindings=(
                        SourceBinding("frame", "host_facets", "architecture"),
                        SourceBinding("constraints", "host_facets", "rules"),
                    ),
                )
            ],
            facet_provider=InMemoryFacetProvider(
                (
                    FacetMaterial(
                        "architecture",
                        "Use explicit adapter protocols and inspectable plans.",
                        "frame",
                        "locked",
                        provenance="example:architecture",
                    ),
                    FacetMaterial(
                        "rules",
                        "Stdlib only; policy must gate every context call.",
                        "constraints",
                        "locked",
                        provenance="example:rules",
                    ),
                    FacetMaterial(
                        "note",
                        "Tone can match the host environment.",
                        "open_vars",
                        "open",
                        provenance="example:open",
                    ),
                )
            ),
        )
    ],
)

result = runtime.plan(
    BridgeRequest(
        request_id="example-packet-1",
        content="Build a new host adapter.",
        policy=ContextPolicy(allow_context=True, max_characters=500),
    )
)
packet = result.plan.field.extensions[CONTEXT_PACKET_ATTACHMENT]
print({"route": result.plan.route.route_id, "packet": packet.to_dict()})
