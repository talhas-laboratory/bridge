"""Configurable characteristic-state router contracts.

Scan content → observe characteristic states → select a context configuration.
Intelligence (OpenClaw/Codex/etc.) plugs in through an optional agent port.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from ...contracts import JsonRecord

ContentKind = Literal["text", "code", "transcript", "table", "html", "json", "other"]
ObservationSource = Literal["deterministic", "agent", "hybrid", "host"]


@dataclass(frozen=True, slots=True)
class ContentEnvelope(JsonRecord):
    """Normalized wrapper so any content type can enter the router."""

    content_id: str
    text: str
    kind: ContentKind = "text"
    uri: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CharacteristicObservation(JsonRecord):
    """Detected state of one characteristic in the scanned content."""

    characteristic_id: str
    state: str
    confidence: float = 0.5
    evidence: tuple[str, ...] = ()
    source: ObservationSource = "deterministic"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphEdge(JsonRecord):
    """Simple typed relation for neighborhood activation."""

    from_id: str
    to_id: str
    relation: str = "related_to"
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class CharacteristicGraph(JsonRecord):
    """Minimal graph substrate: observed nodes + configured edges."""

    nodes: tuple[str, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    active_neighborhood: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextConfiguration(JsonRecord):
    """Router output: what progressive/packet layers should assemble next."""

    configuration_id: str
    lens_id: str = ""
    recipe_id: str = ""
    force_manifest: tuple[str, ...] = ()
    force_define: tuple[str, ...] = ()
    defer: tuple[str, ...] = ()
    source_bindings: tuple[str, ...] = ()
    disclosure_stage: Literal["manifest", "define", "deepen"] = "define"
    density_profile: str = "balanced"
    content_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RouteRule(JsonRecord):
    """Deterministic mapping from characteristic-state patterns to a configuration."""

    rule_id: str
    priority: int = 0
    match_all: Mapping[str, str] = field(default_factory=dict)
    match_any: Mapping[str, str] = field(default_factory=dict)
    configuration: ContextConfiguration = field(
        default_factory=lambda: ContextConfiguration(configuration_id="default")
    )
    description: str = ""


@dataclass(frozen=True, slots=True)
class RoutePolicy(JsonRecord):
    """Configurable router policy pack for a domain/lens."""

    policy_id: str
    rules: tuple[RouteRule, ...]
    graph_edges: tuple[GraphEdge, ...] = ()
    default_configuration: ContextConfiguration = field(
        default_factory=lambda: ContextConfiguration(configuration_id="fallback")
    )
    selection_signals: frozenset[str] = frozenset()
    priority: int = 0
    description: str = ""


@dataclass(frozen=True, slots=True)
class RouteState(JsonRecord):
    """Inspectable router decision."""

    route_id: str
    policy_id: str
    content_id: str
    observations: tuple[CharacteristicObservation, ...] = ()
    matched_rule_ids: tuple[str, ...] = ()
    configuration: ContextConfiguration = field(
        default_factory=lambda: ContextConfiguration(configuration_id="fallback")
    )
    graph: CharacteristicGraph = field(default_factory=CharacteristicGraph)
    rationale: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    agent_assisted: bool = False
