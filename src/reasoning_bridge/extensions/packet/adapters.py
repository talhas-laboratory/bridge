"""Adapter ports owned by the optional context-packet extension."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ...contracts import BridgeRequest, ContextPolicy
from .contracts import ContextPacket, FacetMaterial, PacketRecipe


@runtime_checkable
class FacetProviderPort(Protocol):
    def collect(
        self,
        request: BridgeRequest,
        policy: ContextPolicy,
        recipe: PacketRecipe,
    ) -> tuple[FacetMaterial, ...]: ...


@runtime_checkable
class PacketCompilerPort(Protocol):
    def compile(
        self,
        *,
        recipe: PacketRecipe,
        materials: tuple[FacetMaterial, ...],
        policy: ContextPolicy,
        request_id: str = "",
    ) -> ContextPacket: ...


@dataclass(slots=True)
class InMemoryFacetProvider:
    """Reference facet source for packet compilation tests and host scaffolding."""

    materials: tuple[FacetMaterial, ...] = ()
    calls: list[str] = field(default_factory=list)

    def collect(
        self,
        request: BridgeRequest,
        policy: ContextPolicy,
        recipe: PacketRecipe,
    ) -> tuple[FacetMaterial, ...]:
        self.calls.append(recipe.recipe_id)
        if not policy.allow_context or policy.privacy_mode == "incognito":
            return ()
        allowed_roles = {slot.role for slot in recipe.slots}
        selected = [item for item in self.materials if item.role_hint in allowed_roles]
        if policy.allowed_scopes:
            selected = [item for item in selected if not item.scope or item.scope in policy.allowed_scopes]
        selected = [item for item in selected if not item.scope or item.scope not in policy.excluded_scopes]
        return tuple(selected)
