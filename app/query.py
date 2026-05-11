"""CLI entrypoint for grounded query pipeline."""

from __future__ import annotations

from app.cli import print_cli_banner
import argparse
import sys

from app.config import load_config
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
    plan = router.route(query)
    engine = RetrievalEngine(VectorStore.from_file(runtime.vector_store_path), GraphStore(path=runtime.db_path), ResultStore.from_file(runtime.result_store_path))
    groups = engine.run(query, plan)
    pack = fuse_and_rerank(query, plan, groups)
    answer = GenerationService().generate(pack)
    return {
        "plan": plan.model_dump(),
        "answer": answer.model_dump(),
        "evidence_items": [i.model_dump() for i in pack.items],
    }


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
