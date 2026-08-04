from __future__ import annotations

import json
import unittest

from reasoning_bridge import BridgeRequest, BridgeRuntime, Classification, ContextPolicy
from reasoning_bridge.extensions.router import (
    CONTEXT_CONFIGURATION_ATTACHMENT,
    ROUTE_STATE_ATTACHMENT,
    AgentIntelligenceAdapter,
    CharacteristicRouter,
    CharacteristicRouterExtension,
    ContentEnvelope,
    ContextConfiguration,
    KeywordContentScanner,
    RoutePolicyRegistry,
    activate_neighborhood,
    business_strategy_route_policy,
    match_rule,
)
from reasoning_bridge.extensions.router.contracts import GraphEdge


def _business_scanner() -> KeywordContentScanner:
    return KeywordContentScanner(
        {
            "budget": {"constrained": ("budget", "€40k", "40k", "hard cap")},
            "decision": {"urgent": ("this week", "urgent", "decide now")},
            "service": {"degraded": ("error rate", "timeouts", "degraded")},
            "customer_segment": {"eu_prosumer": ("eu", "creators", "prosumer")},
        }
    )


class CharacteristicRouterTestCase(unittest.TestCase):
    def test_rule_matching_requires_all_and_any(self) -> None:
        policy = business_strategy_route_policy()
        matched = match_rule(policy, {"budget": "constrained", "decision": "urgent"})
        self.assertTrue(matched)
        self.assertEqual(matched[0].rule_id, "budget_constrained_urgent")
        self.assertEqual(match_rule(policy, {"budget": "constrained"}), ())

    def test_neighborhood_activation_expands_graph(self) -> None:
        graph = activate_neighborhood(
            ("budget",),
            (
                GraphEdge("budget", "goal", "constrains"),
                GraphEdge("customer_segment", "goal", "focuses"),
            ),
        )
        self.assertIn("budget", graph.active_neighborhood)
        self.assertIn("goal", graph.active_neighborhood)
        self.assertIn("customer_segment", graph.active_neighborhood)

    def test_router_returns_configuration_for_business_content(self) -> None:
        router = CharacteristicRouter(
            policies=RoutePolicyRegistry((business_strategy_route_policy(),)),
            scanner=_business_scanner(),
        )
        state = router.route(
            ContentEnvelope(
                "c1",
                "We have a €40k hard cap and must decide now for EU creators.",
            ),
            policy=ContextPolicy(allow_context=True),
            signals=frozenset({"domain:business"}),
        )
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.configuration.configuration_id, "budget_push")
        self.assertIn("budget_constrained_urgent", state.matched_rule_ids)
        self.assertIn("budget", state.configuration.force_define)
        self.assertTrue(state.graph.active_neighborhood)
        json.dumps(state.to_dict())

    def test_agent_observations_merge_and_config_requires_trust_flag(self) -> None:
        def backend(payload):
            if payload["operation"] == "propose_observations":
                return {
                    "observations": [
                        {
                            "characteristic_id": "decision",
                            "state": "urgent",
                            "confidence": 0.9,
                            "evidence": ["decide now"],
                        }
                    ]
                }
            return {
                "configuration": {
                    "configuration_id": "agent_override",
                    "lens_id": "business_strategy",
                    "force_define": ["budget"],
                }
            }

        untrusted = AgentIntelligenceAdapter(backend=backend, trust_configuration_proposals=False)
        router = CharacteristicRouter(
            policies=RoutePolicyRegistry((business_strategy_route_policy(),)),
            scanner=KeywordContentScanner({"budget": {"constrained": ("budget",)}}),
            agent=untrusted,
        )
        state = router.route(
            ContentEnvelope("c2", "budget is tight, decide now"),
            policy=ContextPolicy(allow_context=True),
            policy_id="business_strategy_router",
        )
        assert state is not None
        self.assertTrue(state.agent_assisted)
        self.assertEqual(state.configuration.configuration_id, "budget_push")

        trusted = AgentIntelligenceAdapter(backend=backend, trust_configuration_proposals=True)
        router.agent = trusted
        state2 = router.route(
            ContentEnvelope("c3", "budget is tight, decide now"),
            policy=ContextPolicy(allow_context=True),
            policy_id="business_strategy_router",
        )
        assert state2 is not None
        self.assertEqual(state2.configuration.configuration_id, "agent_override")

    def test_runtime_extension_attaches_route_artifacts(self) -> None:
        runtime = BridgeRuntime(
            extensions=[
                CharacteristicRouterExtension(
                    policies=RoutePolicyRegistry((business_strategy_route_policy(),)),
                    scanner=_business_scanner(),
                )
            ]
        )
        denied = runtime.plan(BridgeRequest("r1", "budget decide now", signals=frozenset({"domain:business"})))
        self.assertNotIn(ROUTE_STATE_ATTACHMENT, denied.plan.field.extensions)

        allowed = runtime.plan(
            BridgeRequest(
                "r2",
                "We have a €40k hard cap and must decide now for EU creators.",
                signals=frozenset({"domain:business"}),
                policy=ContextPolicy(allow_context=True),
            )
        )
        self.assertIn(ROUTE_STATE_ATTACHMENT, allowed.plan.field.extensions)
        self.assertIn(CONTEXT_CONFIGURATION_ATTACHMENT, allowed.plan.field.extensions)
        config = allowed.plan.field.extensions[CONTEXT_CONFIGURATION_ATTACHMENT]
        self.assertIsInstance(config, ContextConfiguration)
        self.assertEqual(config.lens_id, "business_strategy")
        self.assertTrue(any(event.get("event") == "characteristic_router_decided" for event in allowed.trace))

    def test_core_runtime_does_not_import_router_extension(self) -> None:
        import reasoning_bridge.runtime as runtime_module
        from pathlib import Path

        source = Path(runtime_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("extensions.router", source)
        self.assertNotIn("ContextConfiguration", source)


if __name__ == "__main__":
    unittest.main()
