from __future__ import annotations

import json
import unittest

from reasoning_bridge import BridgeRequest, BridgeRuntime, Classification, ContextPolicy
from reasoning_bridge.extensions.progressive import (
    DEFINITION_BINDING_ATTACHMENT,
    WORLD_MANIFEST_ATTACHMENT,
    ConstituentKindSpec,
    DefinitionEntry,
    InMemoryDefineProvider,
    InMemoryManifestProvider,
    LensRegistry,
    LensVocabulary,
    ProgressiveDisclosureEngine,
    ProgressiveDisclosureExtension,
    WorldConstituent,
    WorldManifest,
    business_strategy_lens,
    generic_lens,
    select_active_constituents,
)


class ProgressiveDisclosureTestCase(unittest.TestCase):
    def test_lens_registry_selects_domain_vocabulary(self) -> None:
        registry = LensRegistry((generic_lens(), business_strategy_lens()))
        selected = registry.select(frozenset({"domain:business", "goal:strategy"}))
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.lens_id, "business_strategy")
        self.assertIn("budget", selected.kind_ids())

    def test_custom_lens_can_be_populated(self) -> None:
        lens = LensVocabulary(
            lens_id="lab",
            domain="research",
            kinds=(
                ConstituentKindSpec("hypothesis", "Hypothesis", requires_definition_default=True),
                ConstituentKindSpec("dataset", "Dataset"),
            ),
            selection_signals=frozenset({"domain:research"}),
        )
        registry = LensRegistry((lens,))
        self.assertEqual(registry.select(frozenset({"domain:research"})).lens_id, "lab")

    def test_active_selection_prefers_requires_definition_then_salience(self) -> None:
        lens = business_strategy_lens()
        manifest = WorldManifest(
            manifest_id="m1",
            lens_id=lens.lens_id,
            constituents=(
                WorldConstituent("competitor-1", "competitor", "Rival", salience=0.99),
                WorldConstituent("budget-1", "budget", "Budget", salience=0.5, requires_definition=True),
                WorldConstituent("goal-1", "goal", "Goal", salience=0.8, requires_definition=True),
            ),
        )
        active, deferred = select_active_constituents(manifest, lens, max_definitions=2)
        self.assertEqual(active, ("goal-1", "budget-1"))
        self.assertEqual(deferred, ("competitor-1",))

    def test_engine_manifests_then_defines_subset(self) -> None:
        manifest_provider = InMemoryManifestProvider(
            constituents=(
                WorldConstituent("goal-1", "goal", "Grow", salience=0.9, requires_definition=True),
                WorldConstituent("budget-1", "budget", "Budget", salience=0.8, requires_definition=True),
                WorldConstituent("competitor-1", "competitor", "Rival", salience=0.4),
            )
        )
        define_provider = InMemoryDefineProvider(
            (
                DefinitionEntry("goal-1", "Grow to 200 partners.", "locked"),
                DefinitionEntry("budget-1", "Cap at 40k.", "locked"),
                DefinitionEntry("competitor-1", "Ignore unless blocking.", "open"),
            )
        )
        engine = ProgressiveDisclosureEngine(
            lenses=LensRegistry((business_strategy_lens(),)),
            manifest_provider=manifest_provider,
            define_provider=define_provider,
        )
        snapshot = engine.run(
            request=BridgeRequest("r1", "Plan budget.", signals=frozenset({"domain:business"})),
            policy=ContextPolicy(allow_context=True),
            classification=Classification(frozenset({"domain:business"})),
            lens_id="business_strategy",
            max_definitions=2,
        )
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual([item.constituent_id for item in snapshot.manifest.constituents], ["goal-1", "budget-1", "competitor-1"])
        self.assertEqual([item.constituent_id for item in snapshot.binding.definitions], ["goal-1", "budget-1"])
        self.assertEqual(snapshot.binding.deferred, ("competitor-1",))
        json.dumps(snapshot.to_dict())

    def test_manifest_only_mode_without_define_provider(self) -> None:
        engine = ProgressiveDisclosureEngine(
            lenses=LensRegistry((generic_lens(),)),
            manifest_provider=InMemoryManifestProvider(
                constituents=(WorldConstituent("goal-1", "goal", "Ship", salience=0.9, requires_definition=True),)
            ),
            define_provider=None,
        )
        snapshot = engine.run(
            request=BridgeRequest("r2", "Ship it.", policy=ContextPolicy(allow_context=True)),
            policy=ContextPolicy(allow_context=True),
            classification=Classification(frozenset({"word:ship"})),
            lens_id="generic",
        )
        assert snapshot is not None
        self.assertEqual(snapshot.binding.definitions, ())
        self.assertIn("goal-1", snapshot.binding.deferred)
        self.assertIn("define_provider_unavailable_manifest_only", snapshot.binding.warnings)

    def test_runtime_extension_attaches_manifest_and_binding(self) -> None:
        runtime = BridgeRuntime(
            extensions=[
                ProgressiveDisclosureExtension(
                    lenses=LensRegistry((business_strategy_lens(),)),
                    manifest_provider=InMemoryManifestProvider(
                        constituents=(
                            WorldConstituent("goal-1", "goal", "Goal", salience=1.0, requires_definition=True),
                            WorldConstituent("budget-1", "budget", "Budget", salience=0.9, requires_definition=True),
                        )
                    ),
                    define_provider=InMemoryDefineProvider(
                        (
                            DefinitionEntry("goal-1", "Activate partners.", "locked"),
                            DefinitionEntry("budget-1", "40k cap.", "locked"),
                        )
                    ),
                )
            ]
        )
        denied = runtime.plan(BridgeRequest("r3", "Budget plan", signals=frozenset({"domain:business"})))
        self.assertNotIn(WORLD_MANIFEST_ATTACHMENT, denied.plan.field.extensions)

        allowed = runtime.plan(
            BridgeRequest(
                "r4",
                "Budget plan",
                signals=frozenset({"domain:business"}),
                policy=ContextPolicy(allow_context=True),
                metadata={"lens_id": "business_strategy"},
            )
        )
        self.assertIn(WORLD_MANIFEST_ATTACHMENT, allowed.plan.field.extensions)
        self.assertIn(DEFINITION_BINDING_ATTACHMENT, allowed.plan.field.extensions)
        binding = allowed.plan.field.extensions[DEFINITION_BINDING_ATTACHMENT]
        self.assertEqual(len(binding.definitions), 2)
        self.assertTrue(any(event.get("event") == "progressive_disclosure_compiled" for event in allowed.trace))

    def test_core_runtime_does_not_import_progressive_extension(self) -> None:
        import reasoning_bridge.runtime as runtime_module
        from pathlib import Path

        source = Path(runtime_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("extensions.progressive", source)
        self.assertNotIn("WorldManifest", source)


if __name__ == "__main__":
    unittest.main()
