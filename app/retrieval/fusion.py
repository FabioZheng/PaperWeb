"""Multi-store retrieval, score normalization, and reranking."""

from __future__ import annotations

from app.models import EvidencePack, RetrievedItem, RouterPlan


def fuse_and_rerank(query: str, plan: RouterPlan, groups: list[list[RetrievedItem]], top_k: int = 10) -> EvidencePack:
    merged: dict[str, RetrievedItem] = {}
    for items in groups:
        for item in items:
            prev = merged.get(item.item_id)
            if not prev or item.score > prev.score:
                merged[item.item_id] = item

    items = list(merged.values())
    if items:
        max_score = max(i.score for i in items) or 1.0
        for i in items:
            i.score = i.score / max_score
    items.sort(key=lambda i: (i.curated, i.score), reverse=True)
    return EvidencePack(query=query, plan=plan, items=items[:top_k])
