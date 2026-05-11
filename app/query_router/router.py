"""Rule-first query router with optional LLM refinement."""

from __future__ import annotations

from pathlib import Path

from app.extraction.llm_provider import build_provider, render_json_prompt
from app.models import RouterPlan


class QueryRouter:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.provider = build_provider("router")
        self.template = Path("app/prompts/query_routing.txt").read_text(encoding="utf-8")

    def route(self, query: str) -> RouterPlan:
        rule_intent = "comparison" if "compare" in query.lower() else "qa"
        entities = [e for e in ["KILT", "adaptive compression"] if e.lower() in query.lower()]
        base = {
            "intent": rule_intent,
            "entities": entities,
            "filters": {"year_gte": 2024},
            "store_weights": {"vector": 0.4, "graph": 0.2, "result": 0.3, "obsidian": 0.1},
            "retrieval_budget": {"vector": 8, "graph": 4, "result": 6, "obsidian": 4},
            "response_mode": "report" if rule_intent == "comparison" else "answer",
        }
        if not self.use_llm:
            return RouterPlan.model_validate(base)
        llm_out = self.provider.complete_json(render_json_prompt(self.template, {"query": query, "draft": base}))
        merged = {**base, **llm_out}
        return RouterPlan.model_validate(merged)
