from reasoning_bridge import BridgeRequest, BridgeRuntime, ContextPolicy
from reasoning_bridge.extensions.router import (
    CONTEXT_CONFIGURATION_ATTACHMENT,
    ROUTE_STATE_ATTACHMENT,
    AgentIntelligenceAdapter,
    CharacteristicRouterExtension,
    KeywordContentScanner,
    RoutePolicyRegistry,
    business_strategy_route_policy,
)


def openclaw_like_backend(payload: dict):
    """Stand-in for an OpenClaw/Codex agent callback.

    Replace this callable with a real agent client later. It receives a JSON-like
    dict and may return observation/configuration proposals.
    """
    if payload["operation"] == "propose_observations":
        text = payload["content"]["text"].lower()
        observations = []
        if "deadline" in text or "this week" in text:
            observations.append(
                {
                    "characteristic_id": "decision",
                    "state": "urgent",
                    "confidence": 0.8,
                    "evidence": ["this week"],
                }
            )
        return {"observations": observations}
    return {"configuration": None}


runtime = BridgeRuntime(
    extensions=[
        CharacteristicRouterExtension(
            policies=RoutePolicyRegistry((business_strategy_route_policy(),)),
            scanner=KeywordContentScanner(
                {
                    "budget": {"constrained": ("budget", "€40k", "hard cap")},
                    "decision": {"urgent": ("this week", "urgent", "decide")},
                    "customer_segment": {"eu_prosumer": ("eu", "creators")},
                }
            ),
            agent=AgentIntelligenceAdapter(
                backend=openclaw_like_backend,
                trust_configuration_proposals=False,  # keep deterministic policy authoritative
            ),
        )
    ]
)

result = runtime.plan(
    BridgeRequest(
        request_id="route-1",
        content="We have a €40k hard cap for EU creators and must decide this week.",
        signals=frozenset({"domain:business", "goal:strategy"}),
        policy=ContextPolicy(allow_context=True),
    )
)

route_state = result.plan.field.extensions[ROUTE_STATE_ATTACHMENT]
config = result.plan.field.extensions[CONTEXT_CONFIGURATION_ATTACHMENT]
print(
    {
        "matched_rules": list(route_state.matched_rule_ids),
        "observations": {
            item.characteristic_id: item.state for item in route_state.observations
        },
        "configuration_id": config.configuration_id,
        "lens_id": config.lens_id,
        "force_define": list(config.force_define),
        "force_manifest": list(config.force_manifest),
        "graph_neighborhood": list(route_state.graph.active_neighborhood),
        "agent_assisted": route_state.agent_assisted,
        "rationale": list(route_state.rationale),
    }
)
