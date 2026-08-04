"""Plan-time characteristic router extension."""

from __future__ import annotations

from ...contracts import BridgeRequest, Classification, ContextItem, ContextPolicy
from .. import ExtensionContribution
from .adapters import AgentIntelligencePort, ContentScannerPort
from .contracts import ContentEnvelope
from .engine import CharacteristicRouter
from .policies import RoutePolicyRegistry, default_route_policy_registry

ROUTE_STATE_ATTACHMENT = "route_state"
CONTEXT_CONFIGURATION_ATTACHMENT = "context_configuration"


def _policy_id_from_request(request: BridgeRequest) -> str:
    value = request.metadata.get("route_policy_id", "")
    return value if isinstance(value, str) else ""


def _content_from_request(request: BridgeRequest, context: tuple[ContextItem, ...]) -> ContentEnvelope:
    extra = "\n".join(item.content for item in context if item.content)
    text = request.content if not extra else f"{request.content}\n{extra}"
    kind = request.metadata.get("content_kind", "text")
    if kind not in {"text", "code", "transcript", "table", "html", "json", "other"}:
        kind = "text"
    return ContentEnvelope(
        content_id=str(request.metadata.get("content_id", request.request_id)),
        text=text,
        kind=kind,  # type: ignore[arg-type]
        uri=str(request.metadata.get("content_uri", "")),
        metadata=request.metadata,
    )


class CharacteristicRouterExtension:
    """Optional add-on: content → characteristic states → context configuration."""

    def __init__(
        self,
        *,
        policies: RoutePolicyRegistry | None = None,
        scanner: ContentScannerPort,
        agent: AgentIntelligencePort | None = None,
        use_agent_observations: bool = True,
        extension_id: str = "characteristic_router",
    ) -> None:
        self.extension_id = extension_id
        self.router = CharacteristicRouter(
            policies=policies or default_route_policy_registry(),
            scanner=scanner,
            agent=agent,
            use_agent_observations=use_agent_observations,
        )

    def contribute(
        self,
        *,
        request: BridgeRequest,
        policy: ContextPolicy,
        classification: Classification,
        context: tuple[ContextItem, ...],
    ) -> ExtensionContribution:
        if not policy.allow_context:
            return ExtensionContribution(
                trace=({"event": "characteristic_router_skipped", "reason": "policy_denied"},)
            )
        content = _content_from_request(request, context)
        try:
            route_state = self.router.route(
                content,
                policy=policy,
                signals=classification.signals,
                policy_id=_policy_id_from_request(request),
            )
        except Exception as exc:
            return ExtensionContribution(
                warnings=(f"characteristic_router_failed:{type(exc).__name__}",),
                trace=({"event": "characteristic_router_failed", "extension_id": self.extension_id},),
            )
        if route_state is None:
            return ExtensionContribution(
                trace=({"event": "characteristic_router_skipped", "reason": "no_policy_matched"},)
            )
        return ExtensionContribution(
            attachments={
                ROUTE_STATE_ATTACHMENT: route_state,
                CONTEXT_CONFIGURATION_ATTACHMENT: route_state.configuration,
            },
            warnings=route_state.warnings,
            trace=(
                {
                    "event": "characteristic_router_decided",
                    "extension_id": self.extension_id,
                    "policy_id": route_state.policy_id,
                    "configuration_id": route_state.configuration.configuration_id,
                    "matched_rules": list(route_state.matched_rule_ids),
                    "observation_count": len(route_state.observations),
                    "agent_assisted": route_state.agent_assisted,
                    "lens_id": route_state.configuration.lens_id,
                },
            ),
        )
