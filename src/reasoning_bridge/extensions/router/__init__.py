"""Characteristic-state router for configurable context selection."""

from .adapters import (
    AgentIntelligenceAdapter,
    AgentIntelligencePort,
    ContentScannerPort,
    KeywordContentScanner,
)
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
from .engine import CharacteristicRouter, activate_neighborhood, match_rule
from .extension import (
    CONTEXT_CONFIGURATION_ATTACHMENT,
    ROUTE_STATE_ATTACHMENT,
    CharacteristicRouterExtension,
)
from .policies import RoutePolicyRegistry, business_strategy_route_policy, default_route_policy_registry

__all__ = [
    "CONTEXT_CONFIGURATION_ATTACHMENT",
    "ROUTE_STATE_ATTACHMENT",
    "AgentIntelligenceAdapter",
    "AgentIntelligencePort",
    "CharacteristicGraph",
    "CharacteristicObservation",
    "CharacteristicRouter",
    "CharacteristicRouterExtension",
    "ContentEnvelope",
    "ContentScannerPort",
    "ContextConfiguration",
    "GraphEdge",
    "KeywordContentScanner",
    "RoutePolicy",
    "RoutePolicyRegistry",
    "RouteRule",
    "RouteState",
    "activate_neighborhood",
    "business_strategy_route_policy",
    "default_route_policy_registry",
    "match_rule",
]
