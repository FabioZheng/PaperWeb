"""CLI entrypoint for ingestion pipeline."""

from __future__ import annotations

import argparse

from app.consolidation.topic_consolidator import TopicConsolidator
from app.crawlers.mock import ACLCVFStyleCrawler, OpenReviewStyleCrawler
from app.extraction.extractor import ExtractionService
from app.models import Entity
from app.normalization.entity_normalizer import EntityNormalizer
from app.obsidian.notes import ObsidianService
from app.parsing.pdf_parser import PDFParser
from app.storage.graph_store import GraphStore
from app.storage.result_store import ResultStore
from app.storage.structured_db import StructuredDB
from app.storage.vector_store import VectorStore
from app.validation.write_gate import WriteGate


CRAWLERS = {
    "openreview": OpenReviewStyleCrawler,
    "aclcvf": ACLCVFStyleCrawler,
    "mock": OpenReviewStyleCrawler,
}


def run_ingest(source: str, limit: int) -> None:
    crawler = CRAWLERS[source]()
    parser = PDFParser()
    extractor = ExtractionService()
    gate = WriteGate(EntityNormalizer())
    sdb = StructuredDB()
    graph = GraphStore()
    vector = VectorStore.from_file()
    results = ResultStore.from_file()
    obsidian = ObsidianService()

    papers = crawler.fetch_recent(limit=limit)
    all_claims: list[tuple[str, str]] = []
    for paper in papers:
        sdb.upsert_paper(paper)
        chunks = parser.parse(paper)
        sdb.upsert_chunks(chunks)

        extracted = extractor.extract(paper, chunks)
        entities = [
            Entity(entity_id=f"{paper.paper_id}_e0", canonical_name="KILT", aliases=["KILT benchmark"], entity_type="Dataset")
        ]
        validated, norm_entities = gate.validate_and_prepare(extracted, chunks, entities)
        sdb.upsert_extracted(paper.paper_id, validated)

        for c in chunks:
            vector.add(c.chunk_id, c.text, {"paper_id": paper.paper_id, "section": c.section})
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

        obsidian.write_paper_note(paper, paper.abstract)

    for idx, (cid_a, text_a) in enumerate(all_claims):
        for cid_b, text_b in all_claims[idx + 1:]:
            if ("improv" in text_a and "reduce" in text_b) or ("reduce" in text_a and "improv" in text_b):
                graph.add_edge(f"contr_{cid_a}_{cid_b}", cid_a, cid_b, "CONTRADICTS")

    topics = TopicConsolidator().consolidate(papers)
    for t in topics:
        obsidian.write_topic_note(t)
        vector.add(f"topic_{t.topic_id}", t.summary, {"topic": t.topic_name})

    obsidian.reindex_notes(vector)
    vector.save()
    results.save()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="mock", choices=list(CRAWLERS.keys()))
    ap.add_argument("--limit", default=5, type=int)
    args = ap.parse_args()
    run_ingest(args.source, args.limit)


if __name__ == "__main__":
    main()
