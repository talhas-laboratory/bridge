"""Scanner and agent-intelligence ports for the characteristic router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from ...contracts import ContextPolicy
from .contracts import CharacteristicObservation, ContentEnvelope, ContextConfiguration, RouteState

AgentBackend = Callable[[Mapping[str, Any]], Any]


@runtime_checkable
class ContentScannerPort(Protocol):
    """Deterministic or host-owned content scanner."""

    def scan(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
    ) -> tuple[CharacteristicObservation, ...]: ...


@runtime_checkable
class AgentIntelligencePort(Protocol):
    """Optional intelligence hook for OpenClaw, Codex, or other agents.

    Base form is proposal-only: the deterministic policy remains authoritative
    unless a host explicitly trusts agent configuration proposals.
    """

    def propose_observations(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
        seed_observations: tuple[CharacteristicObservation, ...] = (),
    ) -> tuple[CharacteristicObservation, ...]: ...

    def propose_configuration(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
        observations: tuple[CharacteristicObservation, ...],
        route_state: RouteState | None = None,
    ) -> ContextConfiguration | None: ...


class KeywordContentScanner:
    """Simple deterministic scanner: keyword cues → characteristic states."""

    def __init__(
        self,
        cues: dict[str, dict[str, tuple[str, ...] | list[str]]] | None = None,
    ) -> None:
        self.cues = cues or {}
        self.calls: list[str] = []

    def scan(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
    ) -> tuple[CharacteristicObservation, ...]:
        self.calls.append(content.content_id)
        if not policy.allow_context or policy.privacy_mode == "incognito":
            return ()
        text = content.text.lower()
        found: list[CharacteristicObservation] = []
        for characteristic_id, states in self.cues.items():
            for state, keywords in states.items():
                hits = tuple(word for word in keywords if word.lower() in text)
                if hits:
                    found.append(
                        CharacteristicObservation(
                            characteristic_id=characteristic_id,
                            state=state,
                            confidence=min(1.0, 0.45 + 0.1 * len(hits)),
                            evidence=hits,
                            source="deterministic",
                        )
                    )
        return tuple(found)


@dataclass(slots=True)
class AgentIntelligenceAdapter:
    """Thin adapter around a callable agent backend (OpenClaw/Codex/etc.).

    The backend may be any sync callable. Failures become empty proposals so the
    deterministic router can still decide.
    """

    backend: AgentBackend | None = None
    trust_configuration_proposals: bool = False
    calls: list[str] = field(default_factory=list)

    def propose_observations(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
        seed_observations: tuple[CharacteristicObservation, ...] = (),
    ) -> tuple[CharacteristicObservation, ...]:
        self.calls.append(f"observe:{content.content_id}")
        if self.backend is None or not policy.allow_context:
            return ()
        try:
            result = self.backend(
                {
                    "operation": "propose_observations",
                    "content": content.to_dict(),
                    "seed_observations": [item.to_dict() for item in seed_observations],
                    "policy": policy.to_dict(),
                }
            )
        except Exception:
            return ()
        return _parse_observations(result)

    def propose_configuration(
        self,
        content: ContentEnvelope,
        *,
        policy: ContextPolicy,
        observations: tuple[CharacteristicObservation, ...],
        route_state: RouteState | None = None,
    ) -> ContextConfiguration | None:
        self.calls.append(f"configure:{content.content_id}")
        if self.backend is None or not self.trust_configuration_proposals or not policy.allow_context:
            return None
        try:
            result = self.backend(
                {
                    "operation": "propose_configuration",
                    "content": content.to_dict(),
                    "observations": [item.to_dict() for item in observations],
                    "route_state": route_state.to_dict() if route_state else {},
                    "policy": policy.to_dict(),
                }
            )
        except Exception:
            return None
        return _parse_configuration(result)


def _parse_observations(result: Any) -> tuple[CharacteristicObservation, ...]:
    if not isinstance(result, dict):
        return ()
    rows = result.get("observations", ())
    if not isinstance(rows, (list, tuple)):
        return ()
    parsed: list[CharacteristicObservation] = []
    for row in rows:
        if not isinstance(row, dict) or "characteristic_id" not in row or "state" not in row:
            continue
        parsed.append(
            CharacteristicObservation(
                characteristic_id=str(row["characteristic_id"]),
                state=str(row["state"]),
                confidence=float(row.get("confidence", 0.5)),
                evidence=tuple(str(item) for item in row.get("evidence", ())),
                source="agent",
                metadata=row.get("metadata", {}) if isinstance(row.get("metadata", {}), dict) else {},
            )
        )
    return tuple(parsed)


def _parse_configuration(result: Any) -> ContextConfiguration | None:
    if not isinstance(result, dict):
        return None
    payload = result.get("configuration", result)
    if not isinstance(payload, dict) or "configuration_id" not in payload:
        return None
    stage = payload.get("disclosure_stage", "define")
    if stage not in {"manifest", "define", "deepen"}:
        stage = "define"
    return ContextConfiguration(
        configuration_id=str(payload["configuration_id"]),
        lens_id=str(payload.get("lens_id", "")),
        recipe_id=str(payload.get("recipe_id", "")),
        force_manifest=tuple(str(item) for item in payload.get("force_manifest", ())),
        force_define=tuple(str(item) for item in payload.get("force_define", ())),
        defer=tuple(str(item) for item in payload.get("defer", ())),
        source_bindings=tuple(str(item) for item in payload.get("source_bindings", ())),
        disclosure_stage=stage,
        density_profile=str(payload.get("density_profile", "balanced")),
        content_refs=tuple(str(item) for item in payload.get("content_refs", ())),
        metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
    )
