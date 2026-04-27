from app.models import RetrievedItem, RouterPlan
from app.retrieval.fusion import fuse_and_rerank


def test_fusion_dedup_and_sort() -> None:
    plan = RouterPlan(
        intent="qa",
        entities=[],
        filters={},
        store_weights={"vector": 1.0},
        retrieval_budget={"vector": 5},
        response_mode="answer",
    )
    a = RetrievedItem(item_id="x", source_store="vector", text="a", score=0.3, provenance={})
    b = RetrievedItem(item_id="x", source_store="result", text="a2", score=0.8, provenance={})
    c = RetrievedItem(item_id="y", source_store="vector", text="b", score=0.4, provenance={}, curated=True)
    pack = fuse_and_rerank("q", plan, [[a], [b, c]])
    assert len(pack.items) == 2
    assert pack.items[0].item_id == "y"
