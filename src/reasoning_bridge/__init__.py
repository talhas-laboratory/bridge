"""A lightweight, adapter-first reasoning control plane."""

from .adapters import AdapterRegistry, InMemoryContextProvider, InMemoryFacetProvider
from .behaviors import BehaviorRegistry
from .contracts import (
    ActiveField,
    BehaviorSpec,
    BridgeRequest,
    BridgeResult,
    Classification,
    ContextItem,
    ContextPacket,
    ContextPolicy,
    DensityReport,
    ExecutionPlan,
    FacetMaterial,
    PacketRecipe,
    PacketSection,
    PacketSlotSpec,
    RouteDecision,
    SourceBinding,
)
from .packets import DefaultPacketCompiler, RecipeRegistry, context_items_to_materials
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
    "ContextPacket",
    "ContextPolicy",
    "DefaultPacketCompiler",
    "DensityReport",
    "ExecutionPlan",
    "FacetMaterial",
    "InMemoryContextProvider",
    "InMemoryFacetProvider",
    "PacketRecipe",
    "PacketSection",
    "PacketSlotSpec",
    "RecipeRegistry",
    "RouteDecision",
    "SourceBinding",
    "context_items_to_materials",
]
