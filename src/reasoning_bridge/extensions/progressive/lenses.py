"""Lens vocabulary registry and starter domain packs.

Lenses populate kind vocabularies only. Retrieval/providers stay separate so the
same progressive operators can be reused across fields.
"""

from __future__ import annotations

from .contracts import ConstituentKindSpec, LensVocabulary


class LensRegistry:
    def __init__(self, lenses: tuple[LensVocabulary, ...] | list[LensVocabulary] = ()) -> None:
        self._lenses: dict[str, LensVocabulary] = {}
        for lens in lenses:
            self.register(lens)

    def register(self, lens: LensVocabulary, *, replace: bool = False) -> None:
        if not lens.lens_id:
            raise ValueError("lens_id is required")
        if not lens.kinds:
            raise ValueError("lens requires at least one constituent kind")
        if lens.lens_id in self._lenses and not replace:
            raise ValueError(f"lens already registered: {lens.lens_id}")
        ids = [item.kind_id for item in lens.kinds]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate kind ids in lens: {lens.lens_id}")
        self._lenses[lens.lens_id] = lens

    def get(self, lens_id: str) -> LensVocabulary | None:
        return self._lenses.get(lens_id)

    def all(self) -> tuple[LensVocabulary, ...]:
        return tuple(sorted(self._lenses.values(), key=lambda item: (-item.priority, item.lens_id)))

    def select(self, signals: frozenset[str], *, lens_id: str = "") -> LensVocabulary | None:
        if lens_id:
            return self._lenses.get(lens_id)
        for lens in self.all():
            if not lens.selection_signals or lens.selection_signals & signals:
                return lens
        return None


def generic_lens() -> LensVocabulary:
    """Minimal cross-domain vocabulary."""

    return LensVocabulary(
        lens_id="generic",
        domain="general",
        priority=1,
        description="Domain-agnostic constituent kinds for progressive disclosure.",
        kinds=(
            ConstituentKindSpec("actor", "Actor", "Agent or stakeholder in play", "identity"),
            ConstituentKindSpec("goal", "Goal", "Outcome being pursued", "frame", True),
            ConstituentKindSpec("constraint", "Constraint", "Hard limit or forbidden move", "constraints", True),
            ConstituentKindSpec("resource", "Resource", "Available means or asset", "evidence"),
            ConstituentKindSpec("environment", "Environment", "Setting or operating context", "frame"),
            ConstituentKindSpec("tool", "Tool", "Instrument or capability", "evidence"),
            ConstituentKindSpec("risk", "Risk", "Uncertainty or failure mode", "constraints"),
            ConstituentKindSpec("norm", "Norm", "Soft rule, taste, or standard", "anti_caricature"),
        ),
    )


def business_strategy_lens() -> LensVocabulary:
    """Example lens pack for business / strategy / operations."""

    return LensVocabulary(
        lens_id="business_strategy",
        domain="business",
        priority=20,
        selection_signals=frozenset({"domain:business", "goal:strategy", "goal:ops", "word:budget", "word:segment"}),
        description="Starter vocabulary for strategy, GTM, and operations decisions.",
        max_manifest=14,
        max_definitions=7,
        kinds=(
            ConstituentKindSpec("goal", "Goal / OKR", "Current objective", "frame", True),
            ConstituentKindSpec("customer_segment", "Customer segment", "Who is in focus", "identity", True),
            ConstituentKindSpec("offer", "Offer / product", "What is being sold or shipped", "evidence"),
            ConstituentKindSpec("budget", "Budget", "Hard economic constraint", "constraints", True),
            ConstituentKindSpec("capacity", "Capacity", "Team or system throughput constraint", "constraints", True),
            ConstituentKindSpec("competitor", "Competitor / market force", "External pressure", "evidence"),
            ConstituentKindSpec("process", "Process / system", "Operating mechanism in play", "evidence"),
            ConstituentKindSpec("risk", "Risk", "Material downside", "constraints"),
            ConstituentKindSpec("decision_criterion", "Decision criterion", "How options are judged", "constraints", True),
            ConstituentKindSpec("metric", "Metric", "Measurement definition", "evidence", True),
        ),
    )


def default_lens_registry() -> LensRegistry:
    return LensRegistry((generic_lens(), business_strategy_lens()))
