"""Domain-agnostic progressive disclosure contracts.

Manifesting force = which constituents are in play.
Defining force = state-bound meanings for a selected subset.
Lens vocabularies supply domain-specific kinds without changing the operators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from ...contracts import JsonRecord

LockLevel = Literal["locked", "preferred", "suggestive", "open"]


@dataclass(frozen=True, slots=True)
class ConstituentKindSpec(JsonRecord):
    """One vocabulary entry a lens may manifest."""

    kind_id: str
    label: str = ""
    description: str = ""
    default_role_hint: str = "frame"
    requires_definition_default: bool = False


@dataclass(frozen=True, slots=True)
class LensVocabulary(JsonRecord):
    """Domain/lens pack: kinds and defaults only; no retrieval logic."""

    lens_id: str
    domain: str
    kinds: tuple[ConstituentKindSpec, ...]
    selection_signals: frozenset[str] = frozenset()
    priority: int = 0
    max_manifest: int = 12
    max_definitions: int = 6
    description: str = ""

    def kind_ids(self) -> frozenset[str]:
        return frozenset(item.kind_id for item in self.kinds)

    def kind(self, kind_id: str) -> ConstituentKindSpec | None:
        for item in self.kinds:
            if item.kind_id == kind_id:
                return item
        return None


@dataclass(frozen=True, slots=True)
class WorldConstituent(JsonRecord):
    """A manifested piece of the world-in-play."""

    constituent_id: str
    kind: str
    label: str
    salience: float = 0.5
    requires_definition: bool | None = None
    role_hint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorldManifest(JsonRecord):
    """Output of the manifesting force: compositional, light, reusable."""

    manifest_id: str
    lens_id: str
    world_id: str = ""
    request_id: str = ""
    constituents: tuple[WorldConstituent, ...] = ()
    open_questions: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DefinitionEntry(JsonRecord):
    """One state-bound meaning for a manifested constituent."""

    constituent_id: str
    claim: str
    lock_level: LockLevel = "preferred"
    provenance: str = ""
    stereotype_risk: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DefinitionBinding(JsonRecord):
    """Output of the defining force: selective bindings + explicit deferrals."""

    binding_id: str
    manifest_id: str
    lens_id: str
    state_key: str
    request_id: str = ""
    definitions: tuple[DefinitionEntry, ...] = ()
    deferred: tuple[str, ...] = ()
    active: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProgressiveSnapshot(JsonRecord):
    """Paired result of one progressive disclosure turn."""

    lens_id: str
    manifest: WorldManifest
    binding: DefinitionBinding
