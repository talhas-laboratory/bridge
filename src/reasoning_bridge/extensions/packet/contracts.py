"""Contracts owned by the optional context-packet extension."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from ...contracts import JsonRecord

SlotRole = Literal[
    "frame",
    "identity",
    "constraints",
    "evidence",
    "examples",
    "open_vars",
    "anti_caricature",
]
LockLevel = Literal["locked", "preferred", "suggestive", "open"]
DensityProfile = Literal["sparse", "balanced", "dense"]
FillPolicy = Literal["priority", "union", "override"]


@dataclass(frozen=True, slots=True)
class FacetMaterial(JsonRecord):
    """Normalized claim that any source adapter can emit into the compiler."""

    facet_id: str
    claim: str
    role_hint: SlotRole = "evidence"
    lock_level: LockLevel = "preferred"
    confidence: float = 0.5
    salience: float = 0.5
    provenance: str = ""
    scope: str = "host"
    stereotype_risk: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PacketSlotSpec(JsonRecord):
    role: SlotRole
    required: bool = False
    max_characters: int = 0
    fill_policy: FillPolicy = "priority"
    description: str = ""


@dataclass(frozen=True, slots=True)
class SourceBinding(JsonRecord):
    """Declarative mapping from a packet slot to a named source selector."""

    slot_role: SlotRole
    source: str
    selector: str = ""
    max_items: int = 0


@dataclass(frozen=True, slots=True)
class PacketRecipe(JsonRecord):
    """Configurable blueprint for compiling an activation-oriented context packet."""

    recipe_id: str
    priority: int = 0
    activation_goal: str = ""
    slots: tuple[PacketSlotSpec, ...] = ()
    source_bindings: tuple[SourceBinding, ...] = ()
    selection_signals: frozenset[str] = frozenset()
    density_profile: DensityProfile = "balanced"
    max_characters: int = 0
    max_stereotype_risk: float = 0.8
    anti_caricature_rules: tuple[str, ...] = ()
    render_profile: str = "sections_markdown"
    description: str = ""


@dataclass(frozen=True, slots=True)
class PacketSection(JsonRecord):
    role: SlotRole
    materials: tuple[FacetMaterial, ...] = ()
    required: bool = False
    rendered: str = ""


@dataclass(frozen=True, slots=True)
class DensityReport(JsonRecord):
    profile: DensityProfile = "balanced"
    coverage: float = 0.0
    openness: float = 1.0
    used_characters: int = 0
    used_items: int = 0


@dataclass(frozen=True, slots=True)
class ContextPacket(JsonRecord):
    """Compiled activation object: structural grounding without over-prompting."""

    packet_id: str
    recipe_id: str
    activation_goal: str = ""
    request_id: str = ""
    sections: tuple[PacketSection, ...] = ()
    locked_variables: tuple[str, ...] = ()
    open_variables: tuple[str, ...] = ()
    density: DensityReport = field(default_factory=DensityReport)
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
