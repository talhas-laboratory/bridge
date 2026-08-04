"""Versioned, JSON-compatible records exposed by the bridge core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal, Mapping


PROTOCOL_VERSION = "1.0"
RoutingMode = Literal["bias", "override"]
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


class JsonRecord:
    """Small serialization base that keeps public records language-neutral."""

    def to_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, frozenset, set)):
        return [_json_value(item) for item in value]
    if is_dataclass(value):
        return _json_value(asdict(value))
    return value


@dataclass(frozen=True, slots=True)
class BridgeRequest(JsonRecord):
    request_id: str
    content: str
    session_id: str = ""
    operation: Literal["plan", "execute"] = "plan"
    signals: frozenset[str] = frozenset()
    constraints: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    policy: "ContextPolicy" = field(default_factory=lambda: ContextPolicy())
    metadata: Mapping[str, Any] = field(default_factory=dict)
    protocol_version: str = PROTOCOL_VERSION


@dataclass(frozen=True, slots=True)
class ContextPolicy(JsonRecord):
    max_items: int = 0
    max_characters: int = 0
    allowed_scopes: frozenset[str] = frozenset()
    excluded_scopes: frozenset[str] = frozenset()
    allow_context: bool = False
    allow_execution: bool = False
    allow_learning: bool = False
    allow_network: bool = False
    privacy_mode: Literal["standard", "private", "incognito"] = "standard"


@dataclass(frozen=True, slots=True)
class BehaviorSpec(JsonRecord):
    behavior_id: str
    priority: int
    trigger_signals: frozenset[str] = frozenset()
    routing_mode: RoutingMode = "bias"
    preferred_route: str = ""
    directives: tuple[str, ...] = ()
    operator_biases: Mapping[str, bool] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True, slots=True)
class Classification(JsonRecord):
    signals: frozenset[str]
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass(frozen=True, slots=True)
class ContextItem(JsonRecord):
    reference: str
    content: str
    scope: str = "host"
    score: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True, slots=True)
class ActiveField(JsonRecord):
    signals: frozenset[str]
    matched_behavior_ids: tuple[str, ...]
    matched_evidence: Mapping[str, tuple[str, ...]]
    constraints: tuple[str, ...]
    context: tuple[ContextItem, ...]
    confidence: float
    context_packet: ContextPacket | None = None


@dataclass(frozen=True, slots=True)
class RouteDecision(JsonRecord):
    route_id: str
    behavior_ids: tuple[str, ...]
    operator_biases: Mapping[str, bool]
    rationale: tuple[str, ...]
    confidence: float
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionPlan(JsonRecord):
    plan_id: str
    request_id: str
    route: RouteDecision
    field: ActiveField
    policy: ContextPolicy
    directives: tuple[str, ...]
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BridgeResult(JsonRecord):
    plan: ExecutionPlan
    status: Literal["planned", "executed", "degraded", "failed"]
    output: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    trace: tuple[Mapping[str, Any], ...] = ()
