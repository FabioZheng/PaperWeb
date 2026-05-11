"""CLI entrypoint for ingestion pipeline."""

from __future__ import annotations

from app.cli import print_cli_banner
import argparse
import logging
import json
import sys
from collections.abc import Callable

from app.config import load_config
from app.consolidation.topic_consolidator import TopicConsolidator
from app.crawlers.mock import ACLCVFStyleCrawler, OpenReviewStyleCrawler
from app.crawlers.openreview_real import OpenReviewRealCrawler
from app.crawlers.paper_merge import FreshnessTracker, PaperDeduplicator
from app.crawlers.sources import ArxivConnector, OpenAlexConnector, PaperSourceConnector, SemanticScholarConnector
from app.extraction.extractor import ExtractionService
from app.llm.usage_tracker import set_usage_db_path
from app.models import Entity, PaperMetadata
from app.normalization.entity_normalizer import EntityNormalizer
from app.obsidian.notes import ObsidianService
from app.parsing.pdf_parser import PDFParser
from app.runtime import build_runtime_paths
from app.storage.graph_store import GraphStore
from app.storage.semantic_summary import build_semantic_summary
from app.storage.result_store import ResultStore
from app.storage.structured_db import StructuredDB
from app.storage.vector_store import VectorStore
from app.validation.write_gate import WriteGate

LOGGER = logging.getLogger(__name__)

CRAWLERS = {
    "openreview": OpenReviewRealCrawler,
    "aclcvf": ACLCVFStyleCrawler,
    "mock": OpenReviewStyleCrawler,
}

SOURCE_CONNECTORS: dict[str, type[PaperSourceConnector]] = {
    "arxiv": ArxivConnector,
    "openalex": OpenAlexConnector,
    "semantic_scholar": SemanticScholarConnector,
}


def _build_crawler(source: str, research_field: str, paper_type: str, search_query: str | None):
    if source == "openreview":
        return OpenReviewRealCrawler(research_field=research_field, paper_type=paper_type, query=search_query or None)
    return CRAWLERS[source]()


def run_multi_source_ingest(query: str, sources: list[str], limit: int, db_path: str = "data/paperweb.db") -> dict[str, int]:
    fetched: list[PaperMetadata] = []
    failed = 0
    for source in sources:
        connector_cls = SOURCE_CONNECTORS.get(source)
        if not connector_cls:
            LOGGER.warning("Unknown source connector: %s", source)
            failed += 1
            continue
        try:
            fetched.extend(connector_cls().search(query=query, limit=limit))
        except Exception as exc:
            LOGGER.warning("Source %s failed: %s", source, exc)
            failed += 1

    dedup = PaperDeduplicator().deduplicate(fetched)
    tracked, new_count, updated_count = FreshnessTracker().apply(dedup.papers)

    sdb = StructuredDB(path=db_path)
    for paper in tracked:
        sdb.upsert_paper(paper)

    return {
        "fetched": len(fetched),
        "new": new_count,
        "updated": updated_count,
        "duplicates_merged": dedup.duplicates_merged,
        "failed_sources": failed,
    }


def run_ingest(source: str, limit: int, research_field: str = "nlp", paper_type: str = "recent", search_query: str | None = None, *, db_path: str = "data/paperweb.db", usage_db_path: str = "data/llm_usage.sqlite", extraction_enabled: bool = True, topic_inference_enabled: bool = True, semantic_summary_enabled: bool = True, on_event: Callable[[str], None] | None = None) -> None:
    runtime = build_runtime_paths(db_path, usage_db_path)
    set_usage_db_path(runtime.usage_db_path)
    crawler = _build_crawler(source, research_field, paper_type, search_query)
    parser = PDFParser()
    extractor = ExtractionService()
    gate = WriteGate(EntityNormalizer())
    sdb = StructuredDB(path=runtime.db_path)
    graph = GraphStore(path=runtime.db_path)
    vector = VectorStore.from_file(runtime.vector_store_path)
    results = ResultStore.from_file(runtime.result_store_path)
    obsidian = ObsidianService()

    papers = crawler.fetch_recent(limit=limit)
    all_claims: list[tuple[str, str]] = []
    for i, paper in enumerate(papers, start=1):
        if on_event:
            on_event(f"[{i}/{len(papers)}] Ingesting {paper.paper_id}: {paper.title}")
        sdb.upsert_paper(paper)
        graph.add_node(paper.paper_id, "Paper", paper.title[:128])
        sem = build_semantic_summary(paper.title, paper.abstract or "") if semantic_summary_enabled else {"global_summary": paper.abstract or ""}
        graph.upsert_semantic(paper.paper_id, json.dumps(sem))
        chunks = parser.parse(paper)
        sdb.upsert_chunks(chunks)

        if extraction_enabled:
            extracted = extractor.extract(paper, chunks)
            entities = [
                Entity(entity_id=f"{paper.paper_id}_e0", canonical_name="KILT", aliases=["KILT benchmark"], entity_type="Dataset")
            ]
            validated, _ = gate.validate_and_prepare(extracted, chunks, entities)
            sdb.upsert_extracted(paper.paper_id, validated)
        else:
            validated = None

        for c in chunks:
            vector.add(c.chunk_id, c.text, {"paper_id": paper.paper_id, "section": c.section})
        if validated:
            for claim in validated.claims:
                all_claims.append((claim.claim_id, claim.text.lower()))
                vector.add(claim.claim_id, claim.text, {"paper_id": paper.paper_id, "type": "claim"})
                graph.add_node(claim.claim_id, "Claim", claim.text[:64])
                graph.add_edge(f"edge_{paper.paper_id}_{claim.claim_id}", paper.paper_id, claim.claim_id, "MAKES_CLAIM")
            for res in validated.results:
                graph.add_node(res.dataset, "Dataset", res.dataset)
                graph.add_edge(f"eval_{paper.paper_id}_{res.result_id}", paper.paper_id, res.dataset, "EVALUATED_ON")
            if len(validated.claims) > 1:
                graph.add_edge(f"refines_{paper.paper_id}", validated.claims[0].claim_id, validated.claims[-1].claim_id, "REFINES")
            results.add_many(validated.results)

        obsidian.write_paper_note(paper, paper.abstract or "")

    for idx, (cid_a, text_a) in enumerate(all_claims):
        for cid_b, text_b in all_claims[idx + 1 :]:
            if ("improv" in text_a and "reduce" in text_b) or ("reduce" in text_a and "improv" in text_b):
                graph.add_edge(f"contr_{cid_a}_{cid_b}", cid_a, cid_b, "CONTRADICTS")

    if topic_inference_enabled:
        topics = TopicConsolidator().consolidate(papers)
        for t in topics:
            obsidian.write_topic_note(t)
            vector.add(f"topic_{t.topic_id}", t.summary, {"topic": t.topic_name})

    obsidian.reindex_notes(vector)
    vector.save(runtime.vector_store_path)
    results.save(runtime.result_store_path)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    print_cli_banner()
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=cfg.ingestion.source, choices=list(CRAWLERS.keys()))
    ap.add_argument("--limit", default=cfg.ingestion.limit, type=int)
    ap.add_argument("--field", default=cfg.ingestion.research_field, help="Research field (nlp, cv, ml, ai, robotics, all)")
    ap.add_argument("--paper-type", default=cfg.ingestion.paper_type, help="Paper type/keyword (recent, survey, benchmark, ...)")
    ap.add_argument("--search-query", default=cfg.ingestion.search_query or "", help="Optional raw arXiv search_query override")
    ap.add_argument("--query", default="", help="Multi-source discovery query.")
    ap.add_argument("--sources", default="arxiv,semantic_scholar,openalex", help="Comma-separated connectors.")
    args = ap.parse_args()

    if args.query:
        summary = run_multi_source_ingest(args.query, [s.strip() for s in args.sources.split(",") if s.strip()], args.limit, db_path=cfg.storage.db_path)
        print(
            "Fetched={fetched} New={new} Updated={updated} DuplicatesMerged={duplicates_merged} FailedSources={failed_sources}".format(
                **summary
            )
        )
        return

    run_ingest(args.source, args.limit, args.field, args.paper_type, args.search_query or None, db_path=cfg.storage.db_path, usage_db_path=cfg.storage.usage_db_path)


if __name__ == "__main__":
    main()
