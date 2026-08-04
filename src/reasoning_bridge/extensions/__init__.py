"""Optional plan-time extension hooks for the bridge core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from ..contracts import BridgeRequest, Classification, ContextItem, ContextPolicy


@dataclass(frozen=True, slots=True)
class ExtensionContribution:
    """Named artifacts and diagnostics an extension may attach to a plan."""

    attachments: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    trace: tuple[Mapping[str, Any], ...] = ()


@runtime_checkable
class PlanExtension(Protocol):
    """Modular add-on invoked during planning after core context resolution."""

    extension_id: str

    def contribute(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        context: tuple[ContextItem, ...],
    ) -> ExtensionContribution: ...


__all__ = ["ExtensionContribution", "PlanExtension"]
