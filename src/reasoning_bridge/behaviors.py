"""Data-backed behavior registration and deterministic matching."""

from __future__ import annotations

from .contracts import BehaviorSpec


class BehaviorRegistry:
    def __init__(self, behaviors: tuple[BehaviorSpec, ...] | list[BehaviorSpec] = ()) -> None:
        self._behaviors: dict[str, BehaviorSpec] = {}
        for behavior in behaviors:
            self.register(behavior)

    def register(self, behavior: BehaviorSpec, *, replace: bool = False) -> None:
        if not behavior.behavior_id:
            raise ValueError("behavior_id is required")
        if behavior.routing_mode not in {"bias", "override"}:
            raise ValueError(f"unsupported routing mode: {behavior.routing_mode}")
        if behavior.behavior_id in self._behaviors and not replace:
            raise ValueError(f"behavior already registered: {behavior.behavior_id}")
        self._behaviors[behavior.behavior_id] = behavior

    def all(self) -> tuple[BehaviorSpec, ...]:
        return tuple(sorted(self._behaviors.values(), key=lambda item: (-item.priority, item.behavior_id)))

    def match(self, signals: frozenset[str]) -> tuple[tuple[BehaviorSpec, ...], dict[str, tuple[str, ...]]]:
        matched: list[BehaviorSpec] = []
        evidence: dict[str, tuple[str, ...]] = {}
        for behavior in self.all():
            hits = tuple(sorted(behavior.trigger_signals & signals))
            if hits:
                matched.append(behavior)
                evidence[behavior.behavior_id] = hits
        return tuple(matched), evidence
