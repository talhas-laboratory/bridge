"""Plan-time extension that compiles context packets without coupling the core."""

from __future__ import annotations

from ...contracts import BridgeRequest, Classification, ContextItem, ContextPolicy
from .. import ExtensionContribution
from .adapters import FacetProviderPort, PacketCompilerPort
from .compiler import DefaultPacketCompiler, RecipeRegistry, context_items_to_materials
from .contracts import PacketRecipe

CONTEXT_PACKET_ATTACHMENT = "context_packet"


def _recipe_id_from_request(request: BridgeRequest) -> str:
    value = request.metadata.get("recipe_id", "")
    return value if isinstance(value, str) else ""


class ContextPacketExtension:
    """Optional add-on: recipe selection + facet collection + packet compilation."""

    def __init__(
        self,
        *,
        recipes: tuple[PacketRecipe, ...] | list[PacketRecipe] | RecipeRegistry = (),
        facet_provider: FacetProviderPort | None = None,
        compiler: PacketCompilerPort | None = None,
        extension_id: str = "context_packet",
    ) -> None:
        self.extension_id = extension_id
        self.recipes = recipes if isinstance(recipes, RecipeRegistry) else RecipeRegistry(recipes)
        self.facet_provider = facet_provider
        self.compiler: PacketCompilerPort = compiler or DefaultPacketCompiler()

    def contribute(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        context: tuple[ContextItem, ...],
    ) -> ExtensionContribution:
        recipe = self.recipes.select(
            classification.signals,
            recipe_id=_recipe_id_from_request(request),
        )
        if recipe is None:
            return ExtensionContribution()
        if not policy.allow_context:
            return ExtensionContribution(
                trace=(
                    {
                        "event": "context_packet_skipped",
                        "reason": "policy_denied",
                        "recipe_id": recipe.recipe_id,
                    },
                )
            )

        warnings: list[str] = []
        materials = list(context_items_to_materials(context))
        if self.facet_provider is not None:
            try:
                materials.extend(self.facet_provider.collect(request, policy, recipe))
            except Exception as exc:  # adapters are trust boundaries
                warnings.append(f"facet_provider_failed:{type(exc).__name__}")

        try:
            packet = self.compiler.compile(
                recipe=recipe,
                materials=tuple(materials),
                policy=policy,
                request_id=request.request_id,
            )
        except Exception as exc:  # adapters are trust boundaries
            return ExtensionContribution(
                warnings=tuple((*warnings, f"packet_compiler_failed:{type(exc).__name__}")),
                trace=({"event": "context_packet_failed", "recipe_id": recipe.recipe_id},),
            )

        warnings.extend(packet.warnings)
        return ExtensionContribution(
            attachments={CONTEXT_PACKET_ATTACHMENT: packet},
            warnings=tuple(warnings),
            trace=(
                {
                    "event": "context_packet_compiled",
                    "extension_id": self.extension_id,
                    "recipe_id": recipe.recipe_id,
                    "section_count": len(packet.sections),
                    "coverage": packet.density.coverage,
                },
            ),
        )
