"""Deterministic characteristic-state router with optional agent assistance."""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping

from ...contracts import ContextPolicy
from .adapters import AgentIntelligencePort, ContentScannerPort
from .contracts import (
    CharacteristicGraph,
    CharacteristicObservation,
    ContentEnvelope,
    ContextConfiguration,
    GraphEdge,
    RoutePolicy,
    RouteRule,
    RouteState,
)
from .policies import RoutePolicyRegistry


def _route_id(content_id: str, configuration_id: str) -> str:
    digest = sha256(f"{content_id}:{configuration_id}".encode()).hexdigest()[:12]
    return f"route-{digest}"


def _merge_observations(
    primary: tuple[CharacteristicObservation, ...],
    secondary: tuple[CharacteristicObservation, ...],
) -> tuple[CharacteristicObservation, ...]:
    merged: dict[tuple[str, str], CharacteristicObservation] = {}
    for item in (*primary, *secondary):
        key = (item.characteristic_id, item.state)
        prior = merged.get(key)
        if prior is None or item.confidence > prior.confidence:
            merged[key] = item
    return tuple(sorted(merged.values(), key=lambda item: (-item.confidence, item.characteristic_id, item.state)))


def _state_map(observations: tuple[CharacteristicObservation, ...]) -> dict[str, str]:
    best: dict[str, CharacteristicObservation] = {}
    for item in observations:
        current = best.get(item.characteristic_id)
        if current is None or item.confidence > current.confidence:
            best[item.characteristic_id] = item
    return {key: value.state for key, value in best.items()}


def match_rule(policy: RoutePolicy, states: Mapping[str, str]) -> tuple[RouteRule, ...]:
    ranked = sorted(policy.rules, key=lambda item: (-item.priority, item.rule_id))
    matched: list[RouteRule] = []
    for rule in ranked:
        if rule.match_all and any(states.get(key) != value for key, value in rule.match_all.items()):
            continue
        if rule.match_any and not any(states.get(key) == value for key, value in rule.match_any.items()):
            continue
        if not rule.match_all and not rule.match_any:
            continue
        matched.append(rule)
    return tuple(matched)


def activate_neighborhood(
    seed_ids: tuple[str, ...],
    edges: tuple[GraphEdge, ...],
    *,
    max_nodes: int = 12,
) -> CharacteristicGraph:
    nodes = set(seed_ids)
    changed = True
    while changed and len(nodes) < max_nodes:
        changed = False
        for edge in edges:
            if edge.from_id in nodes and edge.to_id not in nodes and len(nodes) < max_nodes:
                nodes.add(edge.to_id)
                changed = True
            if edge.to_id in nodes and edge.from_id not in nodes and len(nodes) < max_nodes:
                nodes.add(edge.from_id)
                changed = True
    active = tuple(sorted(nodes))
    kept_edges = tuple(edge for edge in edges if edge.from_id in nodes and edge.to_id in nodes)
    return CharacteristicGraph(nodes=active, edges=kept_edges, active_neighborhood=active)


def apply_neighborhood_to_configuration(
    configuration: ContextConfiguration,
    neighborhood: CharacteristicGraph,
) -> ContextConfiguration:
    if not neighborhood.active_neighborhood:
        return configuration
    manifest = tuple(dict.fromkeys((*configuration.force_manifest, *neighborhood.active_neighborhood)))
    return ContextConfiguration(
        configuration_id=configuration.configuration_id,
        lens_id=configuration.lens_id,
        recipe_id=configuration.recipe_id,
        force_manifest=manifest,
        force_define=configuration.force_define,
        defer=configuration.defer,
        source_bindings=configuration.source_bindings,
        disclosure_stage=configuration.disclosure_stage,
        density_profile=configuration.density_profile,
        content_refs=configuration.content_refs,
        metadata=configuration.metadata,
    )


class CharacteristicRouter:
    """Scan → observe states → match policy → emit context configuration."""

    def __init__(
        self,
        *,
        policies: RoutePolicyRegistry,
        scanner: ContentScannerPort,
        agent: AgentIntelligencePort | None = None,
        use_agent_observations: bool = True,
    ) -> None:
        self.policies = policies
        self.scanner = scanner
        self.agent = agent
        self.use_agent_observations = use_agent_observations

    def route(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
        signals: frozenset[str] = frozenset(),
        policy_id: str = "",
    ) -> RouteState | None:
        route_policy = self.policies.select(signals, policy_id=policy_id)
        if route_policy is None:
            return None

        warnings: list[str] = []
        observations: tuple[CharacteristicObservation, ...] = ()
        try:
            observations = self.scanner.scan(content, policy=policy)
        except Exception as exc:
            warnings.append(f"scanner_failed:{type(exc).__name__}")

        agent_assisted = False
        if self.agent is not None and self.use_agent_observations and policy.allow_context:
            try:
                proposed = self.agent.propose_observations(
                    content,
                    policy=policy,
                    seed_observations=observations,
                )
                if proposed:
                    observations = _merge_observations(observations, proposed)
                    agent_assisted = True
            except Exception as exc:
                warnings.append(f"agent_observe_failed:{type(exc).__name__}")

        states = _state_map(observations)
        matched = match_rule(route_policy, states)
        if matched:
            chosen_rule = matched[0]
            configuration = chosen_rule.configuration
            matched_ids = tuple(rule.rule_id for rule in matched)
            rationale = (
                f"matched:{chosen_rule.rule_id}",
                *(f"state:{key}={value}" for key, value in sorted(states.items())),
            )
        else:
            configuration = route_policy.default_configuration
            matched_ids = ()
            rationale = ("fallback:default_configuration",)

        if self.agent is not None and policy.allow_context:
            try:
                proposed_config = self.agent.propose_configuration(
                    content,
                    policy=policy,
                    observations=observations,
                )
            except Exception as exc:
                proposed_config = None
                warnings.append(f"agent_configure_failed:{type(exc).__name__}")
            if proposed_config is not None:
                configuration = proposed_config
                agent_assisted = True
                rationale = (*rationale, "agent_configuration_applied")

        seeds = tuple(dict.fromkeys((*states.keys(), *configuration.force_manifest, *configuration.force_define)))
        graph = activate_neighborhood(seeds, route_policy.graph_edges)
        configuration = apply_neighborhood_to_configuration(configuration, graph)

        return RouteState(
            route_id=_route_id(content.content_id, configuration.configuration_id),
            policy_id=route_policy.policy_id,
            content_id=content.content_id,
            observations=observations,
            matched_rule_ids=matched_ids,
            configuration=configuration,
            graph=graph,
            rationale=rationale,
            warnings=tuple(dict.fromkeys(warnings)),
            agent_assisted=agent_assisted,
        )
