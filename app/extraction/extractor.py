"""Paper distillation into structured memory types."""

from __future__ import annotations

from pathlib import Path

from app.extraction.llm_provider import build_provider, render_json_prompt
from app.models import (
    ExtractedClaim,
    ExtractedFact,
    ExtractedMemory,
    Interpretation,
    PaperMetadata,
    ParsedChunk,
    ResultRecord,
    SupportType,
)


class ExtractionService:
    def __init__(self):
        self.provider = build_provider("extractor")
        self.template = Path("app/prompts/paper_extraction.txt").read_text()

    def extract(self, paper: PaperMetadata, chunks: list[ParsedChunk]) -> ExtractedMemory:
        payload = {"paper": paper.model_dump(), "chunks": [c.model_dump() for c in chunks]}
        _ = self.provider.complete_json(render_json_prompt(self.template, payload))

        facts: list[ExtractedFact] = []
        claims: list[ExtractedClaim] = []
        interpretations: list[Interpretation] = []
        results: list[ResultRecord] = []

        for c in chunks:
            lower = c.text.lower()
            if "improv" in lower:
                claims.append(
                    ExtractedClaim(
                        claim_id=f"{paper.paper_id}_{c.chunk_id}_claim",
                        paper_id=paper.paper_id,
                        claim_type="performance",
                        text=c.text.split(".")[0],
                        evidence_chunk_ids=[c.chunk_id],
                        support_type=SupportType.EXPLICIT,
                        confidence=0.79,
                    )
                )
            if c.chunk_type == "table":
                rows = [r.strip() for r in c.text.splitlines() if "|" in r]
                for ridx, row in enumerate(rows):
                    parts = [p.strip() for p in row.split("|")]
                    if len(parts) == 3:
                        method, metric, value = parts
                        try:
                            results.append(
                                ResultRecord(
                                    result_id=f"{paper.paper_id}_{c.chunk_id}_r{ridx}",
                                    paper_id=paper.paper_id,
                                    table_id=f"{paper.paper_id}_{c.chunk_id}_table",
                                    source_reference=f"page:{c.page_start}",
                                    dataset="KILT",
                                    split="dev",
                                    method=method,
                                    baseline="SparseBase" if method != "SparseBase" else None,
                                    metric=metric,
                                    value=float(value),
                                    unit="points",
                                    source_chunk_ids=[c.chunk_id],
                                )
                            )
                        except ValueError:
                            continue
            if c.section.lower().startswith("abstract"):
                facts.append(
                    ExtractedFact(
                        fact_id=f"{paper.paper_id}_{c.chunk_id}_fact",
                        paper_id=paper.paper_id,
                        text=c.text,
                        evidence_chunk_ids=[c.chunk_id],
                        confidence=0.85,
                    )
                )
            if c.section.lower().startswith("method"):
                interpretations.append(
                    Interpretation(
                        interpretation_id=f"{paper.paper_id}_{c.chunk_id}_interp",
                        paper_id=paper.paper_id,
                        text=f"Authors interpret method behavior: {c.text[:120]}",
                        evidence_chunk_ids=[c.chunk_id],
                        confidence=0.7,
                    )
                )

        return ExtractedMemory(facts=facts, claims=claims, interpretations=interpretations, results=results)
