"""Context-packet assembly as an optional bridge extension."""

from .adapters import FacetProviderPort, InMemoryFacetProvider, PacketCompilerPort
from .compiler import DefaultPacketCompiler, RecipeRegistry, context_items_to_materials
from .contracts import (
    ContextPacket,
    DensityReport,
    FacetMaterial,
    PacketRecipe,
    PacketSection,
    PacketSlotSpec,
    SourceBinding,
)
from .extension import CONTEXT_PACKET_ATTACHMENT, ContextPacketExtension

__all__ = [
    "CONTEXT_PACKET_ATTACHMENT",
    "ContextPacket",
    "ContextPacketExtension",
    "DefaultPacketCompiler",
    "DensityReport",
    "FacetMaterial",
    "FacetProviderPort",
    "InMemoryFacetProvider",
    "PacketCompilerPort",
    "PacketRecipe",
    "PacketSection",
    "PacketSlotSpec",
    "RecipeRegistry",
    "SourceBinding",
    "context_items_to_materials",
]
