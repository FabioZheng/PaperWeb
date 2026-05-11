from __future__ import annotations

from uuid import uuid4

from app.agents.tools import (
    generate_grounded_report,
    run_field_intelligence,
    search_graph_neighbors,
    search_semantic_facts,
    search_sql_metadata,
    search_vector_store,
)
from app.agents.tracing import log_trace
from app.config import get_llm_role_config
from app.llm.usage_tracker import estimate_tokens, record_llm_usage


class PaperWebResearchAgent:
    def __init__(self, model_role: str, db_path: str, usage_db_path: str, max_tool_calls: int = 8, trace_enabled: bool = True):
        self.model_role = model_role
        self.db_path = db_path
        self.usage_db_path = usage_db_path
        self.max_tool_calls = max_tool_calls
        self.trace_enabled = trace_enabled
        self.role_cfg = get_llm_role_config(model_role)

    def run(self, query: str, route: str = "agents") -> dict:
        run_id = uuid4().hex[:10]
        calls = []
        evidence = []
        sql = search_sql_metadata(query, {}, self.db_path)
        calls.append({"tool": "search_sql_metadata", "count": len(sql.get("items", []))})
        vec = search_vector_store(query, min(8, self.max_tool_calls), self.db_path)
        calls.append({"tool": "search_vector_store", "count": len(vec.get("items", []))})
        evidence.extend(vec.get("items", []))
        if "compare" in query.lower() or "gap" in query.lower() or "direction" in query.lower() or "review" in query.lower():
            facts = search_semantic_facts(query, 6, self.db_path)
            calls.append({"tool": "search_semantic_facts", "count": len(facts.get("items", []))})
            evidence.extend(facts.get("items", []))
            intel = run_field_intelligence(query, self.db_path)
            calls.append({"tool": "run_field_intelligence", "count": len(intel.get("items", []))})

        report = generate_grounded_report(evidence[:20], self.db_path)
        answer = report["report"]
        in_tok = estimate_tokens(query)
        out_tok = estimate_tokens(answer)
        record_llm_usage(role=self.model_role, provider=self.role_cfg.provider, model=self.role_cfg.model, input_tokens=in_tok, output_tokens=out_tok, source_module="agents", usage_db_path=self.usage_db_path)
        out = {
            "route": route,
            "agent": "paperweb_research",
            "model_role": self.model_role,
            "provider": self.role_cfg.provider,
            "model": self.role_cfg.model,
            "tool_calls": calls,
            "evidence_ids": report.get("evidence_ids", []),
            "answer": answer,
            "run_id": run_id,
        }
        if self.trace_enabled:
            log_trace({"run_id": run_id, "active_db_path": self.db_path, "user_query": query, "selected_route": route, "agent_name": out["agent"], "model_role": self.model_role, "provider": self.role_cfg.provider, "model": self.role_cfg.model, "tool_calls": calls, "evidence_ids_used": out["evidence_ids"], "token_usage": {"input_tokens": in_tok, "output_tokens": out_tok}, "estimated_cost": None, "final_answer": answer, "errors": None})
        return out
