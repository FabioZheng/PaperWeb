"""Retrieval engine dispatching queries across memory backends."""

from __future__ import annotations

from app.models import RetrievedItem, RouterPlan
from app.storage.graph_store import GraphStore
from app.storage.result_store import ResultStore
from app.storage.vector_store import VectorStore


class RetrievalEngine:
    def __init__(self, vector: VectorStore, graph: GraphStore, result: ResultStore):
        self.vector = vector
        self.graph = graph
        self.result = result

    def run(self, query: str, plan: RouterPlan) -> list[list[RetrievedItem]]:
        groups: list[list[RetrievedItem]] = []
        v_budget = plan.retrieval_budget.get("vector", 5)
        groups.append(self.vector.search(query, limit=v_budget))

        r_budget = plan.retrieval_budget.get("result", 5)
        dataset = "KILT" if any(e.lower() == "kilt" for e in plan.entities) else None
        groups.append(self.result.query(dataset=dataset, metric="F1", top_k=r_budget))

        g_budget = plan.retrieval_budget.get("graph", 4)
        graph_items: list[RetrievedItem] = []
        if dataset:
            for pid in self.graph.papers_on_dataset(dataset)[:g_budget]:
                graph_items.append(
                    RetrievedItem(
                        item_id=f"graph_{pid}",
                        source_store="graph",
                        text=f"Paper {pid} evaluated on {dataset}",
                        score=0.6,
                        provenance={"paper_id": pid},
                    )
                )
        groups.append(graph_items)
        return groups
