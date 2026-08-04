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
    ContextPacket,
    ExecutionPlan,
    FacetMaterial,
)
from .packets import DefaultPacketCompiler, RecipeRegistry, context_items_to_materials
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


def _recipe_id_from_request(request: BridgeRequest) -> str:
    value = request.metadata.get("recipe_id", "")
    return value if isinstance(value, str) else ""


class BridgeRuntime:
    def __init__(
        self,
        *,
        behaviors: tuple[Any, ...] | list[Any] = (),
        recipes: tuple[Any, ...] | list[Any] = (),
        adapters: AdapterRegistry | None = None,
    ) -> None:
        self.behaviors = BehaviorRegistry(behaviors)
        self.recipes = RecipeRegistry(recipes)
        self.adapters = adapters or AdapterRegistry()
        self._default_compiler = DefaultPacketCompiler()

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

        behaviors, evidence = self.behaviors.match(classification.signals)
        context_packet: ContextPacket | None = None
        recipe = self.recipes.select(classification.signals, recipe_id=_recipe_id_from_request(request))
        if recipe is not None and policy.allow_context:
            materials: list[FacetMaterial] = list(context_items_to_materials(context))
            if self.adapters.facet_provider is not None:
                try:
                    materials.extend(self.adapters.facet_provider.collect(request, policy, recipe))
                except Exception as exc:  # adapters are trust boundaries
                    warnings.append(f"facet_provider_failed:{type(exc).__name__}")
            compiler = self.adapters.packet_compiler or self._default_compiler
            try:
                context_packet = compiler.compile(
                    recipe=recipe,
                    materials=tuple(materials),
                    policy=policy,
                    request_id=request.request_id,
                )
                warnings.extend(context_packet.warnings)
            except Exception as exc:  # adapters are trust boundaries
                warnings.append(f"packet_compiler_failed:{type(exc).__name__}")
            trace.append(
                {
                    "event": "context_packet_compiled",
                    "recipe_id": recipe.recipe_id,
                    "section_count": len(context_packet.sections) if context_packet else 0,
                    "coverage": context_packet.density.coverage if context_packet else 0.0,
                }
            )
        elif recipe is not None:
            trace.append({"event": "context_packet_skipped", "reason": "policy_denied"})

        field = ActiveField(
            signals=classification.signals,
            matched_behavior_ids=tuple(item.behavior_id for item in behaviors),
            matched_evidence=evidence,
            constraints=request.constraints,
            context=context,
            confidence=classification.confidence,
            context_packet=context_packet,
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
