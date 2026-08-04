"""Ports for the manifesting and defining forces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ...contracts import BridgeRequest, Classification, ContextPolicy
from .contracts import DefinitionEntry, LensVocabulary, WorldConstituent, WorldManifest


@runtime_checkable
class ManifestPort(Protocol):
    def manifest(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        lens: LensVocabulary,
    ) -> WorldManifest: ...


@runtime_checkable
class DefinePort(Protocol):
    def define(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        lens: LensVocabulary,
        manifest: WorldManifest,
        active_ids: tuple[str, ...],
    ) -> tuple[DefinitionEntry, ...]: ...


def _manifest_id(lens_id: str, request_id: str) -> str:
    return f"manifest-{lens_id}-{request_id or 'anon'}"


@dataclass(slots=True)
class InMemoryManifestProvider:
    """Reference manifest source seeded with constituents for tests/hosts."""

    constituents: tuple[WorldConstituent, ...] = ()
    world_id: str = "in_memory"
    provenance: tuple[str, ...] = ()
    calls: list[str] = field(default_factory=list)

    def manifest(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        lens: LensVocabulary,
    ) -> WorldManifest:
        self.calls.append(lens.lens_id)
        if not policy.allow_context or policy.privacy_mode == "incognito":
            return WorldManifest(
                manifest_id=_manifest_id(lens.lens_id, request.request_id),
                lens_id=lens.lens_id,
                world_id=self.world_id,
                request_id=request.request_id,
                warnings=("context_denied_by_policy",),
            )
        allowed = lens.kind_ids()
        selected = [item for item in self.constituents if item.kind in allowed]
        selected.sort(key=lambda item: (-item.salience, item.constituent_id))
        if lens.max_manifest:
            selected = selected[: lens.max_manifest]
        if policy.max_items:
            selected = selected[: policy.max_items]
        return WorldManifest(
            manifest_id=_manifest_id(lens.lens_id, request.request_id),
            lens_id=lens.lens_id,
            world_id=self.world_id,
            request_id=request.request_id,
            constituents=tuple(selected),
            provenance=self.provenance,
        )


class InMemoryDefineProvider:
    """Reference defining source: supplies claims only for requested active ids."""

    def __init__(self, entries: tuple[DefinitionEntry, ...] | list[DefinitionEntry] = ()) -> None:
        self._by_id = {entry.constituent_id: entry for entry in entries}
        self.calls: list[tuple[str, ...]] = []

    def define(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        lens: LensVocabulary,
        manifest: WorldManifest,
        active_ids: tuple[str, ...],
    ) -> tuple[DefinitionEntry, ...]:
        self.calls.append(active_ids)
        if not policy.allow_context or policy.privacy_mode == "incognito":
            return ()
        known = {item.constituent_id for item in manifest.constituents}
        selected: list[DefinitionEntry] = []
        for constituent_id in active_ids:
            if constituent_id not in known:
                continue
            entry = self._by_id.get(constituent_id)
            if entry is not None:
                selected.append(entry)
        return tuple(selected)
