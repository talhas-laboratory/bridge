"""Small orchestration runtime with explicit, policy-gated adapter calls."""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

from .adapters import AdapterRegistry
from .behaviors import BehaviorRegistry
from .contracts import (
    ActiveField,
    BridgeRequest,
    BridgeResult,
    Classification,
    ExecutionPlan,
)
from .extensions import ExtensionContribution, PlanExtension
from .policy import normalize_policy
from .routing import resolve_route


def _local_classification(request: BridgeRequest) -> Classification:
    words = frozenset(re.findall(r"[a-z0-9_]+", request.content.lower()))
    signals = set(request.signals)
    signals.update(f"word:{word}" for word in words)
    if words & {"build", "implement", "scaffold", "architecture"}:
        signals.add("goal:build")
    if words & {"evaluate", "risk", "novel", "feasible"}:
        signals.add("goal:evaluate")
    if words & {"symbolic", "meaning", "subconscious", "archetype"}:
        signals.add("mode:interpretive")
    return Classification(frozenset(signals), confidence=0.5, source="deterministic")


def _plan_id(request_id: str, route_id: str) -> str:
    digest = sha256(f"{request_id}:{route_id}".encode()).hexdigest()[:16]
    return f"plan-{digest}"


def _run_extensions(
    extensions: tuple[PlanExtension, ...],
    *,
    request: BridgeRequest,
    policy: Any,
    classification: Classification,
    context: tuple[Any, ...],
) -> ExtensionContribution:
    attachments: dict[str, Any] = {}
    warnings: list[str] = []
    trace: list[dict[str, Any]] = []
    for extension in extensions:
        try:
            contribution = extension.contribute(
                request=request,
                policy=policy,
                classification=classification,
                context=context,
            )
        except Exception as exc:  # extensions are trust boundaries
            warnings.append(f"extension_failed:{extension.extension_id}:{type(exc).__name__}")
            trace.append({"event": "extension_failed", "extension_id": extension.extension_id})
            continue
        attachments.update(contribution.attachments)
        warnings.extend(contribution.warnings)
        trace.extend(dict(item) for item in contribution.trace)
    return ExtensionContribution(
        attachments=attachments,
        warnings=tuple(warnings),
        trace=tuple(trace),
    )


class BridgeRuntime:
    def __init__(
        self,
        *,
        behaviors: tuple[Any, ...] | list[Any] = (),
        adapters: AdapterRegistry | None = None,
        extensions: tuple[PlanExtension, ...] | list[PlanExtension] = (),
    ) -> None:
        self.behaviors = BehaviorRegistry(behaviors)
        self.adapters = adapters or AdapterRegistry()
        self.extensions: tuple[PlanExtension, ...] = tuple(extensions)

    def plan(self, request: BridgeRequest) -> BridgeResult:
        policy = normalize_policy(request.policy)
        trace: list[dict[str, Any]] = [{"event": "request_received", "request_id": request.request_id}]
        warnings: list[str] = []

        classification = _local_classification(request)
        if self.adapters.classifier is not None:
            try:
                classification = self.adapters.classifier.classify(request)
            except Exception as exc:  # adapters are trust boundaries
                warnings.append(f"classifier_failed:{type(exc).__name__}")
        trace.append({"event": "classified", "source": classification.source, "signal_count": len(classification.signals)})

        context = ()
        if policy.allow_context and self.adapters.context_provider is not None:
            try:
                context = self.adapters.context_provider.retrieve(request, policy)
            except Exception as exc:  # adapters are trust boundaries
                warnings.append(f"context_provider_failed:{type(exc).__name__}")
        trace.append({"event": "context_resolved", "item_count": len(context)})

        contribution = _run_extensions(
            self.extensions,
            request=request,
            policy=policy,
            classification=classification,
            context=context,
        )
        warnings.extend(contribution.warnings)
        trace.extend(dict(item) for item in contribution.trace)

        behaviors, evidence = self.behaviors.match(classification.signals)
        field = ActiveField(
            signals=classification.signals,
            matched_behavior_ids=tuple(item.behavior_id for item in behaviors),
            matched_evidence=evidence,
            constraints=request.constraints,
            context=context,
            confidence=classification.confidence,
            extensions=contribution.attachments,
        )
        route = resolve_route(behaviors, confidence=classification.confidence)
        directives = tuple(directive for behavior in behaviors for directive in behavior.directives)
        required = ("executor",) if request.operation == "execute" else ()
        plan = ExecutionPlan(
            plan_id=_plan_id(request.request_id, route.route_id),
            request_id=request.request_id,
            route=route,
            field=field,
            policy=policy,
            directives=directives,
            required_capabilities=required,
        )
        trace.append({"event": "route_selected", "route": route.route_id, "behaviors": route.behavior_ids})
        self._emit(trace[-1])
        return BridgeResult(plan=plan, status="degraded" if warnings else "planned", warnings=tuple(warnings), trace=tuple(trace))

    def execute(self, request: BridgeRequest) -> BridgeResult:
        result = self.plan(request)
        if not request.policy.allow_execution:
            return BridgeResult(result.plan, "failed", warnings=(*result.warnings, "execution_denied_by_policy"), trace=result.trace)
        if self.adapters.executor is None:
            return BridgeResult(result.plan, "degraded", warnings=(*result.warnings, "executor_unavailable"), trace=result.trace)
        try:
            output = self.adapters.executor.execute(result.plan)
        except Exception as exc:  # adapters are trust boundaries
            return BridgeResult(result.plan, "failed", warnings=(*result.warnings, f"executor_failed:{type(exc).__name__}"), trace=result.trace)
        return BridgeResult(result.plan, "executed", output=output, warnings=result.warnings, trace=result.trace)

    def _emit(self, event: dict[str, Any]) -> None:
        if self.adapters.telemetry is None:
            return
        try:
            self.adapters.telemetry.emit(event)
        except Exception:
            pass
