from reasoning_bridge import (
    AdapterRegistry,
    BehaviorSpec,
    BridgeRequest,
    BridgeRuntime,
    ContextItem,
    ContextPolicy,
    InMemoryContextProvider,
)


runtime = BridgeRuntime(
    behaviors=[
        BehaviorSpec(
            behavior_id="implementation",
            priority=80,
            trigger_signals=frozenset({"goal:build"}),
            routing_mode="bias",
            preferred_route="implementation",
            directives=("produce_a_small_next_slice",),
        )
    ],
    adapters=AdapterRegistry(
        context_provider=InMemoryContextProvider(
            (ContextItem("architecture", "Use explicit adapter protocols.", "project"),)
        )
    ),
)

result = runtime.plan(
    BridgeRequest(
        request_id="example-1",
        content="Build a new host adapter.",
        policy=ContextPolicy(allow_context=True, max_items=2),
    )
)
print(result.to_dict())
