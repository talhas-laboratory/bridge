from __future__ import annotations

import json
import unittest

from reasoning_bridge import (
    AdapterRegistry,
    BehaviorSpec,
    BridgeRequest,
    BridgeRuntime,
    Classification,
    ContextItem,
    ContextPolicy,
    DefaultPacketCompiler,
    FacetMaterial,
    InMemoryContextProvider,
    InMemoryFacetProvider,
    PacketRecipe,
    PacketSlotSpec,
    RecipeRegistry,
)


def _steering_recipe() -> PacketRecipe:
    return PacketRecipe(
        recipe_id="implementation_steering",
        priority=50,
        activation_goal="implementation_agent",
        selection_signals=frozenset({"goal:build"}),
        density_profile="balanced",
        max_characters=400,
        max_stereotype_risk=0.7,
        anti_caricature_rules=("prefer realistic competence over caricature",),
        slots=(
            PacketSlotSpec("frame", required=True, max_characters=120),
            PacketSlotSpec("constraints", required=True, max_characters=120),
            PacketSlotSpec("evidence", required=False, max_characters=160),
            PacketSlotSpec("open_vars", required=False, max_characters=80),
            PacketSlotSpec("anti_caricature", required=False, max_characters=80),
        ),
        source_bindings=(),
    )


class RuntimeTestCase(unittest.TestCase):
    def test_plans_without_any_adapter(self) -> None:
        result = BridgeRuntime().plan(BridgeRequest("request-1", "Explain the bridge."))
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.plan.route.route_id, "default")
        self.assertEqual(result.plan.field.context, ())
        self.assertIsNone(result.plan.field.context_packet)
        json.dumps(result.to_dict())

    def test_override_beats_bias_and_preserves_generic_biases(self) -> None:
        runtime = BridgeRuntime(
            behaviors=[
                BehaviorSpec("scaffold", 80, frozenset({"goal:build"}), "bias", "implementation", operator_biases={"actionable": True}),
                BehaviorSpec("safe_build", 90, frozenset({"goal:build"}), "override", "reviewed_implementation", operator_biases={"review": True}),
            ]
        )
        result = runtime.plan(BridgeRequest("request-2", "Build this."))
        self.assertEqual(result.plan.route.route_id, "reviewed_implementation")
        self.assertEqual(result.plan.route.behavior_ids, ("safe_build", "scaffold"))
        self.assertEqual(result.plan.route.operator_biases, {"review": True, "actionable": True})

    def test_context_is_policy_gated_and_bounded(self) -> None:
        provider = InMemoryContextProvider(
            (
                ContextItem("one", "first", "project"),
                ContextItem("two", "second", "project"),
            )
        )
        runtime = BridgeRuntime(adapters=AdapterRegistry(context_provider=provider))
        denied = runtime.plan(BridgeRequest("request-3", "Build."))
        self.assertEqual(denied.plan.field.context, ())
        self.assertEqual(provider.calls, [])
        allowed = runtime.plan(BridgeRequest("request-4", "Build.", policy=ContextPolicy(allow_context=True, max_items=1)))
        self.assertEqual([item.reference for item in allowed.plan.field.context], ["one"])

    def test_incognito_removes_context_and_learning_capabilities(self) -> None:
        provider = InMemoryContextProvider((ContextItem("one", "secret", "project"),))
        runtime = BridgeRuntime(adapters=AdapterRegistry(context_provider=provider))
        result = runtime.plan(BridgeRequest("request-5", "Build.", policy=ContextPolicy(allow_context=True, allow_learning=True, privacy_mode="incognito")))
        self.assertFalse(result.plan.policy.allow_context)
        self.assertFalse(result.plan.policy.allow_learning)
        self.assertEqual(provider.calls, [])

    def test_classifier_failure_is_structured_and_deterministic_fallback_remains(self) -> None:
        class FailingClassifier:
            def classify(self, request: BridgeRequest) -> Classification:
                raise RuntimeError("offline")

        runtime = BridgeRuntime(adapters=AdapterRegistry(classifier=FailingClassifier()))
        result = runtime.plan(BridgeRequest("request-6", "Build."))
        self.assertIn("classifier_failed:RuntimeError", result.warnings)
        self.assertEqual(result.plan.route.route_id, "default")

    def test_execution_requires_explicit_policy_and_adapter(self) -> None:
        runtime = BridgeRuntime()
        result = runtime.execute(BridgeRequest("request-7", "Execute.", operation="execute"))
        self.assertEqual(result.status, "failed")
        self.assertIn("execution_denied_by_policy", result.warnings)


class PacketInfrastructureTestCase(unittest.TestCase):
    def test_recipe_registry_selects_by_signal_and_explicit_id(self) -> None:
        registry = RecipeRegistry([_steering_recipe()])
        matched = registry.select(frozenset({"goal:build"}))
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(matched.recipe_id, "implementation_steering")
        self.assertIsNone(registry.select(frozenset({"goal:evaluate"})))
        explicit = registry.select(frozenset(), recipe_id="implementation_steering")
        self.assertEqual(explicit.recipe_id if explicit else None, "implementation_steering")

    def test_default_compiler_builds_locked_and_open_sections(self) -> None:
        compiler = DefaultPacketCompiler()
        packet = compiler.compile(
            recipe=_steering_recipe(),
            materials=(
                FacetMaterial("frame-1", "Adapter-first control plane.", "frame", "locked", salience=0.9, provenance="doc:frame"),
                FacetMaterial("constraint-1", "Stdlib only; no hidden network calls.", "constraints", "locked", salience=0.8, provenance="doc:rules"),
                FacetMaterial("evidence-1", "Use explicit packet recipes.", "evidence", "preferred", salience=0.7, provenance="doc:evidence"),
                FacetMaterial("open-1", "Tone may adapt to the host.", "open_vars", "open", salience=0.4),
                FacetMaterial("risky", "Always act like a genius loner hacker.", "identity", "suggestive", stereotype_risk=0.95),
            ),
            policy=ContextPolicy(allow_context=True, max_characters=500),
            request_id="packet-1",
        )
        roles = [section.role for section in packet.sections]
        self.assertEqual(roles, ["frame", "constraints", "evidence", "open_vars"])
        self.assertTrue(any(item.startswith("frame:") for item in packet.locked_variables))
        self.assertTrue(packet.density.coverage >= 1.0)
        self.assertGreater(packet.density.openness, 0.0)
        self.assertIn("prefer realistic competence over caricature", " ".join(packet.open_variables))
        json.dumps(packet.to_dict())

    def test_runtime_compiles_packet_from_facets_when_recipe_matches(self) -> None:
        facets = InMemoryFacetProvider(
            (
                FacetMaterial("frame-1", "Build a small next slice.", "frame", "locked", provenance="facet:frame"),
                FacetMaterial("constraint-1", "Keep adapters explicit.", "constraints", "locked", provenance="facet:rules"),
            )
        )
        runtime = BridgeRuntime(
            recipes=[_steering_recipe()],
            adapters=AdapterRegistry(facet_provider=facets),
        )
        denied = runtime.plan(BridgeRequest("request-8", "Build an adapter."))
        self.assertIsNone(denied.plan.field.context_packet)
        self.assertEqual(facets.calls, [])

        allowed = runtime.plan(
            BridgeRequest(
                "request-9",
                "Build an adapter.",
                policy=ContextPolicy(allow_context=True, max_characters=300),
            )
        )
        packet = allowed.plan.field.context_packet
        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertEqual(packet.recipe_id, "implementation_steering")
        self.assertEqual(packet.activation_goal, "implementation_agent")
        self.assertEqual(facets.calls, ["implementation_steering"])
        self.assertTrue(any(event.get("event") == "context_packet_compiled" for event in allowed.trace))

    def test_context_items_can_feed_compiler_via_role_metadata(self) -> None:
        provider = InMemoryContextProvider(
            (
                ContextItem("frame-ref", "Host integration task.", "project", 0.9, {"role": "frame", "lock_level": "locked"}),
                ContextItem("rule-ref", "No silent fallbacks.", "project", 0.8, {"role": "constraints", "lock_level": "locked"}),
            )
        )
        runtime = BridgeRuntime(
            recipes=[_steering_recipe()],
            adapters=AdapterRegistry(context_provider=provider),
        )
        result = runtime.plan(
            BridgeRequest(
                "request-10",
                "Build this.",
                policy=ContextPolicy(allow_context=True),
                metadata={"recipe_id": "implementation_steering"},
            )
        )
        packet = result.plan.field.context_packet
        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertGreaterEqual(len(packet.sections), 2)
        self.assertIn("frame-ref", packet.provenance)


if __name__ == "__main__":
    unittest.main()
