"""Route policy registry and starter configurable packs."""

from __future__ import annotations

from .contracts import ContextConfiguration, GraphEdge, RoutePolicy, RouteRule


class RoutePolicyRegistry:
    def __init__(self, policies: tuple[RoutePolicy, ...] | list[RoutePolicy] = ()) -> None:
        self._policies: dict[str, RoutePolicy] = {}
        for policy in policies:
            self.register(policy)

    def register(self, policy: RoutePolicy, *, replace: bool = False) -> None:
        if not policy.policy_id:
            raise ValueError("policy_id is required")
        if policy.policy_id in self._policies and not replace:
            raise ValueError(f"route policy already registered: {policy.policy_id}")
        self._policies[policy.policy_id] = policy

    def get(self, policy_id: str) -> RoutePolicy | None:
        return self._policies.get(policy_id)

    def all(self) -> tuple[RoutePolicy, ...]:
        return tuple(sorted(self._policies.values(), key=lambda item: (-item.priority, item.policy_id)))

    def select(self, signals: frozenset[str], *, policy_id: str = "") -> RoutePolicy | None:
        if policy_id:
            return self._policies.get(policy_id)
        for policy in self.all():
            if not policy.selection_signals or policy.selection_signals & signals:
                return policy
        return None


def business_strategy_route_policy() -> RoutePolicy:
    """Starter configurable policy for business/strategy content."""

    return RoutePolicy(
        policy_id="business_strategy_router",
        priority=20,
        selection_signals=frozenset({"domain:business", "goal:strategy", "goal:ops"}),
        description="Route business content into progressive strategy configurations.",
        graph_edges=(
            GraphEdge("budget", "goal", "constrains"),
            GraphEdge("customer_segment", "goal", "focuses"),
            GraphEdge("capacity", "budget", "limits"),
            GraphEdge("competitor", "goal", "pressures"),
        ),
        default_configuration=ContextConfiguration(
            configuration_id="business_default",
            lens_id="business_strategy",
            recipe_id="",
            force_manifest=("goal", "budget", "customer_segment"),
            force_define=("goal",),
            disclosure_stage="manifest",
            density_profile="balanced",
        ),
        rules=(
            RouteRule(
                rule_id="budget_constrained_urgent",
                priority=100,
                match_all={"budget": "constrained"},
                match_any={"decision": "urgent", "urgency": "high"},
                description="Constrained budget + urgency → define budget/segment/criteria.",
                configuration=ContextConfiguration(
                    configuration_id="budget_push",
                    lens_id="business_strategy",
                    force_manifest=("goal", "budget", "customer_segment", "decision_criterion", "capacity"),
                    force_define=("goal", "budget", "customer_segment", "decision_criterion"),
                    defer=("competitor",),
                    source_bindings=("okrs", "finance", "gtm"),
                    disclosure_stage="define",
                    density_profile="balanced",
                ),
            ),
            RouteRule(
                rule_id="incident_ops",
                priority=90,
                match_all={"service": "degraded"},
                description="Degraded service → ops deepen configuration.",
                configuration=ContextConfiguration(
                    configuration_id="ops_incident",
                    lens_id="business_strategy",
                    force_manifest=("process", "risk", "capacity", "goal"),
                    force_define=("process", "risk", "capacity"),
                    source_bindings=("runbooks", "status"),
                    disclosure_stage="deepen",
                    density_profile="dense",
                ),
            ),
        ),
    )


def default_route_policy_registry() -> RoutePolicyRegistry:
    return RoutePolicyRegistry((business_strategy_route_policy(),))
