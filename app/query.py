"""CLI entrypoint for grounded query pipeline."""

from __future__ import annotations

from app.cli import print_cli_banner
import argparse
import sys

from app.config import load_config
from app.agents.config import parse_agents_config
from app.agents.paperweb_agent import PaperWebResearchAgent
from app.generation.generator import GenerationService
from app.llm.usage_tracker import set_usage_db_path
from app.query_router.router import QueryRouter
from app.retrieval.engine import RetrievalEngine
from app.retrieval.fusion import fuse_and_rerank
from app.runtime import build_runtime_paths
from app.storage.graph_store import GraphStore
from app.storage.result_store import ResultStore
from app.storage.vector_store import VectorStore


def run_query(query: str, *, db_path: str = "data/paperweb.db", usage_db_path: str = "data/llm_usage.sqlite") -> dict:
    runtime = build_runtime_paths(db_path, usage_db_path)
    set_usage_db_path(runtime.usage_db_path)
    router = QueryRouter(use_llm=True)
    cfg = load_config()
    route = router.select_execution_route(query)
    if route == "agents":
        acfg = parse_agents_config(cfg, {"agents": cfg.agents or {}})
        role = acfg.research.model_role
        try:
            agent_out = PaperWebResearchAgent(model_role=role, db_path=runtime.db_path, usage_db_path=runtime.usage_db_path, max_tool_calls=acfg.research.max_tool_calls, trace_enabled=acfg.trace_enabled).run(query, route="agents")
            return {"route": "agents", "plan": {"intent": "multi_step_research"}, "answer": {"query": query, "answer": agent_out["answer"], "citations": agent_out.get("evidence_ids", []), "mode": "report"}, "evidence_items": [], "tool_calls": agent_out.get("tool_calls", [])}
        except Exception as exc:
            route = "pipeline"
            fallback_reason = str(exc)
    plan = router.route(query)
    engine = RetrievalEngine(VectorStore.from_file(runtime.vector_store_path), GraphStore(path=runtime.db_path), ResultStore.from_file(runtime.result_store_path))
    groups = engine.run(query, plan)
    pack = fuse_and_rerank(query, plan, groups)
    answer = GenerationService().generate(pack)
    out = {
        "route": "pipeline",
        "plan": plan.model_dump(),
        "answer": answer.model_dump(),
        "evidence_items": [i.model_dump() for i in pack.items],
    }
    if "fallback_reason" in locals():
        out["agent_fallback_reason"] = fallback_reason
    return out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    print_cli_banner()
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    args = ap.parse_args()
    import json

    print(json.dumps(run_query(args.query, db_path=cfg.storage.db_path, usage_db_path=cfg.storage.usage_db_path), indent=2))


if __name__ == "__main__":
    main()
