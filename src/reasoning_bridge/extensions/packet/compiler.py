"""Declarative context-packet recipes and a deterministic default compiler."""

from __future__ import annotations

from hashlib import sha256

from ...contracts import ContextItem, ContextPolicy
from .contracts import (
    ContextPacket,
    DensityProfile,
    DensityReport,
    FacetMaterial,
    LockLevel,
    PacketRecipe,
    PacketSection,
    PacketSlotSpec,
    SlotRole,
)

DEFAULT_SLOT_ORDER: tuple[SlotRole, ...] = (
    "frame",
    "identity",
    "constraints",
    "evidence",
    "examples",
    "open_vars",
    "anti_caricature",
)

_LOCK_RANK: dict[LockLevel, int] = {
    "locked": 3,
    "preferred": 2,
    "suggestive": 1,
    "open": 0,
}

_DENSITY_FILL: dict[DensityProfile, float] = {
    "sparse": 0.35,
    "balanced": 0.7,
    "dense": 0.9,
}


class RecipeRegistry:
    def __init__(self, recipes: tuple[PacketRecipe, ...] | list[PacketRecipe] = ()) -> None:
        self._recipes: dict[str, PacketRecipe] = {}
        for recipe in recipes:
            self.register(recipe)

    def register(self, recipe: PacketRecipe, *, replace: bool = False) -> None:
        if not recipe.recipe_id:
            raise ValueError("recipe_id is required")
        if not recipe.slots:
            raise ValueError("packet recipe requires at least one slot")
        if recipe.density_profile not in _DENSITY_FILL:
            raise ValueError(f"unsupported density profile: {recipe.density_profile}")
        if recipe.recipe_id in self._recipes and not replace:
            raise ValueError(f"recipe already registered: {recipe.recipe_id}")
        self._recipes[recipe.recipe_id] = recipe

    def get(self, recipe_id: str) -> PacketRecipe | None:
        return self._recipes.get(recipe_id)

    def all(self) -> tuple[PacketRecipe, ...]:
        return tuple(sorted(self._recipes.values(), key=lambda item: (-item.priority, item.recipe_id)))

    def select(self, signals: frozenset[str], *, recipe_id: str = "") -> PacketRecipe | None:
        if recipe_id:
            return self._recipes.get(recipe_id)
        for recipe in self.all():
            if not recipe.selection_signals or recipe.selection_signals & signals:
                return recipe
        return None


def context_items_to_materials(items: tuple[ContextItem, ...]) -> tuple[FacetMaterial, ...]:
    materials: list[FacetMaterial] = []
    for index, item in enumerate(items):
        role = item.metadata.get("role", "evidence")
        if role not in DEFAULT_SLOT_ORDER:
            role = "evidence"
        lock = item.metadata.get("lock_level", "preferred")
        if lock not in _LOCK_RANK:
            lock = "preferred"
        materials.append(
            FacetMaterial(
                facet_id=item.reference or f"context-item-{index}",
                claim=item.content,
                role_hint=role,  # type: ignore[arg-type]
                lock_level=lock,  # type: ignore[arg-type]
                confidence=item.score if item.score else 0.5,
                salience=item.score if item.score else 0.5,
                provenance=item.reference,
                scope=item.scope,
                stereotype_risk=float(item.metadata.get("stereotype_risk", 0.0)),
                metadata=item.metadata,
            )
        )
    return tuple(materials)


def _packet_id(recipe_id: str, material_ids: tuple[str, ...]) -> str:
    digest = sha256(f"{recipe_id}:{','.join(material_ids)}".encode()).hexdigest()[:16]
    return f"packet-{digest}"


def _slot_map(recipe: PacketRecipe) -> dict[SlotRole, PacketSlotSpec]:
    return {slot.role: slot for slot in recipe.slots}


def _eligible(material: FacetMaterial, policy: ContextPolicy) -> bool:
    if policy.allowed_scopes and material.scope and material.scope not in policy.allowed_scopes:
        return False
    if material.scope and material.scope in policy.excluded_scopes:
        return False
    return True


def _sort_key(material: FacetMaterial) -> tuple[float, float, float, str]:
    return (
        -_LOCK_RANK[material.lock_level],
        -material.salience,
        -material.confidence,
        material.facet_id,
    )


class DefaultPacketCompiler:
    """Deterministic compiler: select → rank → budget → render."""

    def compile(
        self,
        *,
        recipe: PacketRecipe,
        materials: tuple[FacetMaterial, ...],
        policy: ContextPolicy,
        request_id: str = "",
    ) -> ContextPacket:
        if policy.privacy_mode == "incognito" or not policy.allow_context:
            return ContextPacket(
                packet_id=_packet_id(recipe.recipe_id, ()),
                recipe_id=recipe.recipe_id,
                activation_goal=recipe.activation_goal,
                request_id=request_id,
                density=DensityReport(profile=recipe.density_profile),
                warnings=("context_denied_by_policy",),
            )

        slots = _slot_map(recipe)
        fill_ratio = _DENSITY_FILL[recipe.density_profile]
        selected: dict[SlotRole, list[FacetMaterial]] = {role: [] for role in slots}
        used_chars = 0
        warnings: list[str] = []
        global_budget = policy.max_characters or recipe.max_characters or 0

        ranked = sorted((item for item in materials if _eligible(item, policy)), key=_sort_key)
        if policy.max_items:
            ranked = ranked[: policy.max_items]

        for material in ranked:
            role = material.role_hint if material.role_hint in slots else None
            if role is None:
                continue
            slot = slots[role]
            if material.stereotype_risk > recipe.max_stereotype_risk and role != "anti_caricature":
                warnings.append(f"stereotype_risk_skipped:{material.facet_id}")
                continue
            slot_budget = slot.max_characters or 0
            slot_used = sum(len(item.claim) for item in selected[role])
            remaining_slot = (slot_budget - slot_used) if slot_budget else None
            remaining_global = (global_budget - used_chars) if global_budget else None
            if remaining_slot is not None and remaining_slot <= 0:
                continue
            if remaining_global is not None and remaining_global <= 0:
                warnings.append("global_character_budget_exhausted")
                break

            claim = material.claim
            limits = [limit for limit in (remaining_slot, remaining_global) if limit is not None]
            if limits:
                claim = claim[: min(limits)]
            if not claim:
                continue

            target_chars = int(slot_budget * fill_ratio) if slot_budget else None
            if target_chars is not None and slot_used >= target_chars and material.lock_level != "locked":
                continue

            chosen = FacetMaterial(
                facet_id=material.facet_id,
                claim=claim,
                role_hint=role,
                lock_level=material.lock_level,
                confidence=material.confidence,
                salience=material.salience,
                provenance=material.provenance,
                scope=material.scope,
                stereotype_risk=material.stereotype_risk,
                metadata=material.metadata,
            )
            selected[role].append(chosen)
            used_chars += len(claim)

        sections: list[PacketSection] = []
        locked_vars: list[str] = []
        open_vars: list[str] = []
        provenance: list[str] = []
        required_roles = 0
        filled_required = 0

        for role in DEFAULT_SLOT_ORDER:
            if role not in slots:
                continue
            slot = slots[role]
            items = tuple(selected[role])
            if slot.required:
                required_roles += 1
                if items:
                    filled_required += 1
                else:
                    warnings.append(f"missing_required_slot:{role}")
            if not items and not slot.required:
                continue
            sections.append(
                PacketSection(
                    role=role,
                    materials=items,
                    required=slot.required,
                    rendered="\n".join(item.claim for item in items),
                )
            )
            for item in items:
                if item.provenance:
                    provenance.append(item.provenance)
                label = item.claim if len(item.claim) <= 80 else f"{item.claim[:77]}..."
                if item.lock_level == "locked":
                    locked_vars.append(f"{role}:{label}")
                elif item.lock_level == "open" or role == "open_vars":
                    open_vars.append(f"{role}:{label}")

        for rule in recipe.anti_caricature_rules:
            if "anti_caricature" in slots and not any(
                rule == item.claim for item in selected.get("anti_caricature", ())
            ):
                # Surface recipe guards as open steering hints when not already present.
                open_vars.append(f"anti_caricature:{rule}")

        coverage = (filled_required / required_roles) if required_roles else 1.0
        openness = 1.0
        if locked_vars or open_vars:
            openness = len(open_vars) / (len(locked_vars) + len(open_vars))

        material_ids = tuple(item.facet_id for section in sections for item in section.materials)
        return ContextPacket(
            packet_id=_packet_id(recipe.recipe_id, material_ids),
            recipe_id=recipe.recipe_id,
            activation_goal=recipe.activation_goal,
            request_id=request_id,
            sections=tuple(sections),
            locked_variables=tuple(dict.fromkeys(locked_vars)),
            open_variables=tuple(dict.fromkeys(open_vars)),
            density=DensityReport(
                profile=recipe.density_profile,
                coverage=round(coverage, 4),
                openness=round(openness, 4),
                used_characters=used_chars,
                used_items=sum(len(section.materials) for section in sections),
            ),
            provenance=tuple(dict.fromkeys(provenance)),
            warnings=tuple(dict.fromkeys(warnings)),
        )
