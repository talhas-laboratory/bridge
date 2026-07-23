from __future__ import annotations

import unittest
import json

from reasoning_bridge import (
    AdapterRegistry,
    BehaviorSpec,
    BridgeRequest,
    BridgeRuntime,
    Classification,
    ContextItem,
    ContextPolicy,
    InMemoryContextProvider,
)


class RuntimeTestCase(unittest.TestCase):
    def test_plans_without_any_adapter(self) -> None:
        result = BridgeRuntime().plan(BridgeRequest("request-1", "Explain the bridge."))
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.plan.route.route_id, "default")
        self.assertEqual(result.plan.field.context, ())
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


if __name__ == "__main__":
    unittest.main()
