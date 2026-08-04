"""Deterministic progressive disclosure engine: manifest → select → define → defer."""

from __future__ import annotations

from hashlib import sha256

from ...contracts import BridgeRequest, Classification, ContextPolicy
from .adapters import DefinePort, ManifestPort
from .contracts import (
    DefinitionBinding,
    LensVocabulary,
    ProgressiveSnapshot,
    WorldConstituent,
    WorldManifest,
)
from .lenses import LensRegistry


def _state_key(request: BridgeRequest, classification: Classification, lens_id: str) -> str:
    signal_part = ",".join(sorted(classification.signals))
    raw = f"{request.request_id}|{request.session_id}|{lens_id}|{signal_part}|{request.content[:160]}"
    return sha256(raw.encode()).hexdigest()[:16]


def _binding_id(manifest_id: str, state_key: str) -> str:
    return f"binding-{sha256(f'{manifest_id}:{state_key}'.encode()).hexdigest()[:12]}"


def _requires_definition(constituent: WorldConstituent, lens: LensVocabulary) -> bool:
    if constituent.requires_definition is not None:
        return constituent.requires_definition
    kind = lens.kind(constituent.kind)
    return bool(kind.requires_definition_default) if kind is not None else False


def select_active_constituents(
    manifest: WorldManifest,
    lens: LensVocabulary,
    *,
    max_definitions: int | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Choose which manifested constituents receive definitions this turn."""

    limit = lens.max_definitions if max_definitions is None else max_definitions
    ranked = sorted(manifest.constituents, key=lambda item: (-item.salience, item.constituent_id))
    required = [item for item in ranked if _requires_definition(item, lens)]
    optional = [item for item in ranked if not _requires_definition(item, lens)]
    chosen: list[WorldConstituent] = []
    for item in required + optional:
        if len(chosen) >= limit:
            break
        chosen.append(item)
    active = tuple(item.constituent_id for item in chosen)
    deferred = tuple(item.constituent_id for item in ranked if item.constituent_id not in set(active))
    return active, deferred


def validate_manifest(manifest: WorldManifest, lens: LensVocabulary) -> tuple[WorldManifest, tuple[str, ...]]:
    allowed = lens.kind_ids()
    warnings: list[str] = list(manifest.warnings)
    kept: list[WorldConstituent] = []
    for item in manifest.constituents:
        if item.kind not in allowed:
            warnings.append(f"unknown_kind_skipped:{item.kind}:{item.constituent_id}")
            continue
        kept.append(item)
    if tuple(kept) == manifest.constituents and tuple(warnings) == manifest.warnings:
        return manifest, tuple(warnings)
    cleaned = WorldManifest(
        manifest_id=manifest.manifest_id,
        lens_id=manifest.lens_id or lens.lens_id,
        world_id=manifest.world_id,
        request_id=manifest.request_id,
        constituents=tuple(kept),
        open_questions=manifest.open_questions,
        provenance=manifest.provenance,
        warnings=tuple(dict.fromkeys(warnings)),
    )
    return cleaned, cleaned.warnings


class ProgressiveDisclosureEngine:
    """Runs the two-force loop against a lens vocabulary."""

    def __init__(
        self,
        *,
        lenses: LensRegistry,
        manifest_provider: ManifestPort,
        define_provider: DefinePort | None = None,
    ) -> None:
        self.lenses = lenses
        self.manifest_provider = manifest_provider
        self.define_provider = define_provider

    def run(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        lens_id: str = "",
        max_definitions: int | None = None,
    ) -> ProgressiveSnapshot | None:
        lens = self.lenses.select(classification.signals, lens_id=lens_id)
        if lens is None:
            return None

        manifest = self.manifest_provider.manifest(
            request=request,
            policy=policy,
            classification=classification,
            lens=lens,
        )
        manifest, manifest_warnings = validate_manifest(manifest, lens)
        active, deferred = select_active_constituents(manifest, lens, max_definitions=max_definitions)
        state_key = _state_key(request, classification, lens.lens_id)

        definitions = ()
        define_warnings: list[str] = []
        if active and self.define_provider is not None and policy.allow_context and policy.privacy_mode != "incognito":
            try:
                definitions = self.define_provider.define(
                    request=request,
                    policy=policy,
                    classification=classification,
                    lens=lens,
                    manifest=manifest,
                    active_ids=active,
                )
            except Exception as exc:  # providers are trust boundaries
                define_warnings.append(f"define_provider_failed:{type(exc).__name__}")
        elif active and self.define_provider is None:
            # Manifest-only mode is valid: state can steer from labels/kinds.
            deferred = active + deferred
            active = ()
            define_warnings.append("define_provider_unavailable_manifest_only")

        defined_ids = {item.constituent_id for item in definitions}
        missing = tuple(item for item in active if item not in defined_ids)
        if missing:
            define_warnings.append("missing_definitions:" + ",".join(missing))
            deferred = tuple(dict.fromkeys(missing + deferred))
            active = tuple(item for item in active if item in defined_ids)

        binding = DefinitionBinding(
            binding_id=_binding_id(manifest.manifest_id, state_key),
            manifest_id=manifest.manifest_id,
            lens_id=lens.lens_id,
            state_key=state_key,
            request_id=request.request_id,
            definitions=definitions,
            deferred=deferred,
            active=active,
            provenance=tuple(dict.fromkeys(item.provenance for item in definitions if item.provenance)),
            warnings=tuple(dict.fromkeys((*manifest_warnings, *define_warnings))),
        )
        return ProgressiveSnapshot(lens_id=lens.lens_id, manifest=manifest, binding=binding)
