"""Policy normalization and capability-safe defaults."""

from __future__ import annotations

from dataclasses import replace

from .contracts import ContextPolicy


def normalize_policy(policy: ContextPolicy) -> ContextPolicy:
    if policy.max_items < 0 or policy.max_characters < 0:
        raise ValueError("context budgets cannot be negative")
    if policy.privacy_mode == "incognito":
        return replace(
            policy,
            allow_context=False,
            allow_learning=False,
            allow_network=False,
            max_items=0,
            max_characters=0,
        )
    return policy
