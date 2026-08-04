"""Narrow adapter protocols and dependency-free reference adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from .contracts import (
    BridgeRequest,
    Classification,
    ContextItem,
    ContextPolicy,
    ExecutionPlan,
)


@runtime_checkable
class ClassifierPort(Protocol):
    def classify(self, request: BridgeRequest) -> Classification: ...


@runtime_checkable
class ContextProviderPort(Protocol):
    def retrieve(self, request: BridgeRequest, policy: ContextPolicy) -> tuple[ContextItem, ...]: ...


@runtime_checkable
class ExecutorPort(Protocol):
    def execute(self, plan: ExecutionPlan) -> dict[str, Any]: ...


@runtime_checkable
class LearningPort(Protocol):
    def record(self, event: Mapping[str, Any]) -> None: ...


@runtime_checkable
class TelemetryPort(Protocol):
    def emit(self, event: Mapping[str, Any]) -> None: ...


@dataclass(slots=True)
class AdapterRegistry:
    classifier: ClassifierPort | None = None
    context_provider: ContextProviderPort | None = None
    executor: ExecutorPort | None = None
    learning: LearningPort | None = None
    telemetry: TelemetryPort | None = None

    def capabilities(self) -> frozenset[str]:
        names = {
            "classify": self.classifier,
            "context": self.context_provider,
            "execute": self.executor,
            "learn": self.learning,
            "telemetry": self.telemetry,
        }
        return frozenset(name for name, adapter in names.items() if adapter is not None)


@dataclass(slots=True)
class InMemoryContextProvider:
    """Reference adapter useful for tests, examples, and host conformance work."""

    items: tuple[ContextItem, ...] = ()
    calls: list[ContextPolicy] = field(default_factory=list)

    def retrieve(self, request: BridgeRequest, policy: ContextPolicy) -> tuple[ContextItem, ...]:
        self.calls.append(policy)
        if not policy.allow_context or policy.privacy_mode == "incognito":
            return ()
        allowed = policy.allowed_scopes
        excluded = policy.excluded_scopes
        selected = [
            item
            for item in self.items
            if (not allowed or item.scope in allowed) and item.scope not in excluded
        ]
        if policy.max_items:
            selected = selected[: policy.max_items]
        if policy.max_characters:
            remaining = policy.max_characters
            bounded: list[ContextItem] = []
            for item in selected:
                if remaining <= 0:
                    break
                content = item.content[:remaining]
                bounded.append(ContextItem(item.reference, content, item.scope, item.score, item.metadata))
                remaining -= len(content)
            selected = bounded
        return tuple(selected)
