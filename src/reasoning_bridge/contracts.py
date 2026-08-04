"""Versioned, JSON-compatible records exposed by the bridge core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal, Mapping


PROTOCOL_VERSION = "1.0"
RoutingMode = Literal["bias", "override"]


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
class ActiveField(JsonRecord):
    signals: frozenset[str]
    matched_behavior_ids: tuple[str, ...]
    matched_evidence: Mapping[str, tuple[str, ...]]
    constraints: tuple[str, ...]
    context: tuple[ContextItem, ...]
    confidence: float
    extensions: Mapping[str, Any] = field(default_factory=dict)


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
