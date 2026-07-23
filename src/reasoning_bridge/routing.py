"""Deterministic route selection from activated behaviors."""

from __future__ import annotations

from .contracts import BehaviorSpec, RouteDecision


DEFAULT_ROUTE = "default"


def resolve_route(
    behaviors: tuple[BehaviorSpec, ...],
    *,
    confidence: float,
) -> RouteDecision:
    overrides = [item for item in behaviors if item.routing_mode == "override" and item.preferred_route]
    selected = overrides[0].preferred_route if overrides else DEFAULT_ROUTE
    if not overrides:
        biases_with_routes = [item for item in behaviors if item.preferred_route]
        if biases_with_routes:
            selected = biases_with_routes[0].preferred_route

    biases: dict[str, bool] = {}
    directives: list[str] = []
    for behavior in behaviors:
        biases.update(behavior.operator_biases)
        directives.extend(behavior.directives)
    rationale = tuple(
        f"behavior:{behavior.behavior_id}:{behavior.routing_mode}" for behavior in behaviors
    ) or ("fallback:default",)
    alternatives = tuple(
        dict.fromkeys(
            behavior.preferred_route
            for behavior in behaviors
            if behavior.preferred_route and behavior.preferred_route != selected
        )
    )
    return RouteDecision(
        route_id=selected,
        behavior_ids=tuple(behavior.behavior_id for behavior in behaviors),
        operator_biases=biases,
        rationale=rationale,
        confidence=confidence,
        alternatives=alternatives,
    )
