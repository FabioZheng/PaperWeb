from app.query_router.router import QueryRouter


def test_router_plan_generation() -> None:
    router = QueryRouter(use_llm=False)
    plan = router.route("Compare adaptive compression methods on KILT")
    assert plan.intent == "comparison"
    assert "KILT" in plan.entities
    assert "vector" in plan.store_weights
