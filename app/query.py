"""CLI entrypoint for grounded query pipeline."""

from __future__ import annotations

from app.cli import print_cli_banner
import argparse

from app.generation.generator import GenerationService
from app.query_router.router import QueryRouter
from app.retrieval.engine import RetrievalEngine
from app.retrieval.fusion import fuse_and_rerank
from app.storage.graph_store import GraphStore
from app.storage.result_store import ResultStore
from app.storage.vector_store import VectorStore


def run_query(query: str) -> str:
    router = QueryRouter(use_llm=True)
    plan = router.route(query)
    engine = RetrievalEngine(VectorStore.from_file(), GraphStore(), ResultStore.from_file())
    groups = engine.run(query, plan)
    pack = fuse_and_rerank(query, plan, groups)
    answer = GenerationService().generate(pack)
    return answer.model_dump_json(indent=2)


def main() -> None:
    print_cli_banner()
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    args = ap.parse_args()
    print(run_query(args.query))


if __name__ == "__main__":
    main()
