"""A lightweight, adapter-first reasoning control plane."""

from .adapters import AdapterRegistry, InMemoryContextProvider
from .behaviors import BehaviorRegistry
from .contracts import (
    ActiveField,
    BehaviorSpec,
    BridgeRequest,
    BridgeResult,
    Classification,
    ContextItem,
    ContextPolicy,
    ExecutionPlan,
    RouteDecision,
)
from .extensions import ExtensionContribution, PlanExtension
from .runtime import BridgeRuntime

__all__ = [
    "ActiveField",
    "AdapterRegistry",
    "BehaviorRegistry",
    "BehaviorSpec",
    "BridgeRequest",
    "BridgeResult",
    "BridgeRuntime",
    "Classification",
    "ContextItem",
    "ContextPolicy",
    "ExecutionPlan",
    "ExtensionContribution",
    "InMemoryContextProvider",
    "PlanExtension",
    "RouteDecision",
]
