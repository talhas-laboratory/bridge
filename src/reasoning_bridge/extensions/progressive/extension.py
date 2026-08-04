"""Plan-time progressive disclosure extension with swappable lens vocabularies."""

from __future__ import annotations

from ...contracts import BridgeRequest, Classification, ContextItem, ContextPolicy
from .. import ExtensionContribution
from .adapters import DefinePort, ManifestPort
from .engine import ProgressiveDisclosureEngine
from .lenses import LensRegistry, default_lens_registry

WORLD_MANIFEST_ATTACHMENT = "world_manifest"
DEFINITION_BINDING_ATTACHMENT = "definition_binding"
PROGRESSIVE_SNAPSHOT_ATTACHMENT = "progressive_snapshot"


def _lens_id_from_request(request: BridgeRequest) -> str:
    value = request.metadata.get("lens_id", "")
    return value if isinstance(value, str) else ""


class ProgressiveDisclosureExtension:
    """Optional add-on: manifesting force + defining force over a lens vocabulary."""

    def __init__(
        self,
        *,
        lenses: LensRegistry | None = None,
        manifest_provider: ManifestPort,
        define_provider: DefinePort | None = None,
        extension_id: str = "progressive_disclosure",
        max_definitions: int | None = None,
    ) -> None:
        self.extension_id = extension_id
        self.max_definitions = max_definitions
        self.engine = ProgressiveDisclosureEngine(
            lenses=lenses or default_lens_registry(),
            manifest_provider=manifest_provider,
            define_provider=define_provider,
        )

    def contribute(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        context: tuple[ContextItem, ...],
    ) -> ExtensionContribution:
        del context  # progressive providers own composition; core context remains available to other extensions
        if not policy.allow_context:
            return ExtensionContribution(
                trace=({"event": "progressive_disclosure_skipped", "reason": "policy_denied"},)
            )
        try:
            snapshot = self.engine.run(
                request=request,
                policy=policy,
                classification=classification,
                lens_id=_lens_id_from_request(request),
                max_definitions=self.max_definitions,
            )
        except Exception as exc:  # extensions are trust boundaries
            return ExtensionContribution(
                warnings=(f"progressive_disclosure_failed:{type(exc).__name__}",),
                trace=({"event": "progressive_disclosure_failed", "extension_id": self.extension_id},),
            )
        if snapshot is None:
            return ExtensionContribution(
                trace=({"event": "progressive_disclosure_skipped", "reason": "no_lens_matched"},)
            )

        warnings = tuple(dict.fromkeys((*snapshot.manifest.warnings, *snapshot.binding.warnings)))
        return ExtensionContribution(
            attachments={
                WORLD_MANIFEST_ATTACHMENT: snapshot.manifest,
                DEFINITION_BINDING_ATTACHMENT: snapshot.binding,
                PROGRESSIVE_SNAPSHOT_ATTACHMENT: snapshot,
            },
            warnings=warnings,
            trace=(
                {
                    "event": "progressive_disclosure_compiled",
                    "extension_id": self.extension_id,
                    "lens_id": snapshot.lens_id,
                    "manifested": len(snapshot.manifest.constituents),
                    "defined": len(snapshot.binding.definitions),
                    "deferred": len(snapshot.binding.deferred),
                },
            ),
        )
