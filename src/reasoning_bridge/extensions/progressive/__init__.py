"""Progressive disclosure: manifesting + defining forces with lens vocabularies."""

from .adapters import DefinePort, InMemoryDefineProvider, InMemoryManifestProvider, ManifestPort
from .contracts import (
    ConstituentKindSpec,
    DefinitionBinding,
    DefinitionEntry,
    LensVocabulary,
    ProgressiveSnapshot,
    WorldConstituent,
    WorldManifest,
)
from .engine import ProgressiveDisclosureEngine, select_active_constituents
from .extension import (
    DEFINITION_BINDING_ATTACHMENT,
    PROGRESSIVE_SNAPSHOT_ATTACHMENT,
    WORLD_MANIFEST_ATTACHMENT,
    ProgressiveDisclosureExtension,
)
from .lenses import LensRegistry, business_strategy_lens, default_lens_registry, generic_lens

__all__ = [
    "DEFINITION_BINDING_ATTACHMENT",
    "PROGRESSIVE_SNAPSHOT_ATTACHMENT",
    "WORLD_MANIFEST_ATTACHMENT",
    "ConstituentKindSpec",
    "DefinePort",
    "DefinitionBinding",
    "DefinitionEntry",
    "InMemoryDefineProvider",
    "InMemoryManifestProvider",
    "LensRegistry",
    "LensVocabulary",
    "ManifestPort",
    "ProgressiveDisclosureEngine",
    "ProgressiveDisclosureExtension",
    "ProgressiveSnapshot",
    "WorldConstituent",
    "WorldManifest",
    "business_strategy_lens",
    "default_lens_registry",
    "generic_lens",
    "select_active_constituents",
]
