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
        self.template = Path("app/prompts/paper_extraction.txt").read_text(encoding="utf-8")

    def extract(self, paper: PaperMetadata, chunks: list[ParsedChunk]) -> ExtractedMemory:
        payload = {"paper": paper.model_dump(), "chunks": [c.model_dump() for c in chunks]}
        llm_out = self.provider.complete_json(render_json_prompt(self.template, payload))

        valid_chunk_ids = {c.chunk_id for c in chunks}

        facts = self._parse_facts(llm_out.get("facts", []), paper.paper_id, valid_chunk_ids)
        claims = self._parse_claims(llm_out.get("claims", []), paper.paper_id, valid_chunk_ids)
        interpretations = self._parse_interpretations(
            llm_out.get("interpretations", []),
            paper.paper_id,
            valid_chunk_ids,
        )
        results = self._parse_results(llm_out.get("results", []), paper.paper_id, valid_chunk_ids)

        if not any((facts, claims, interpretations, results)):
            # Minimal fallback: bind first chunk as a fact to keep pipeline robust.
            fallback_chunk = chunks[0]
            facts = [
                ExtractedFact(
                    fact_id=f"{paper.paper_id}_{fallback_chunk.chunk_id}_fact_0",
                    paper_id=paper.paper_id,
                    text=fallback_chunk.text[:1000],
                    evidence_chunk_ids=[fallback_chunk.chunk_id],
                    confidence=0.6,
                )
            ]

        return ExtractedMemory(facts=facts, claims=claims, interpretations=interpretations, results=results)

    def _parse_facts(self, items: list[dict], paper_id: str, valid_chunk_ids: set[str]) -> list[ExtractedFact]:
        out: list[ExtractedFact] = []
        for idx, item in enumerate(items):
            evidence = self._valid_evidence(item.get("evidence_chunk_ids", []), valid_chunk_ids)
            if not evidence:
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            out.append(
                ExtractedFact(
                    fact_id=item.get("fact_id") or f"{paper_id}_fact_{idx}",
                    paper_id=paper_id,
                    text=text,
                    evidence_chunk_ids=evidence,
                    confidence=_clamp_conf(item.get("confidence", 0.7)),
                )
            )
        return out

    def _parse_claims(self, items: list[dict], paper_id: str, valid_chunk_ids: set[str]) -> list[ExtractedClaim]:
        out: list[ExtractedClaim] = []
        for idx, item in enumerate(items):
            evidence = self._valid_evidence(item.get("evidence_chunk_ids", []), valid_chunk_ids)
            if not evidence:
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            support_type = str(item.get("support_type", "explicit")).lower()
            if support_type not in {"explicit", "table_derived", "llm_inferred"}:
                support_type = "explicit"
            out.append(
                ExtractedClaim(
                    claim_id=item.get("claim_id") or f"{paper_id}_claim_{idx}",
                    paper_id=paper_id,
                    claim_type=str(item.get("claim_type", "general")),
                    text=text,
                    evidence_chunk_ids=evidence,
                    support_type=SupportType(support_type),
                    confidence=_clamp_conf(item.get("confidence", 0.7)),
                )
            )
        return out

    def _parse_interpretations(self, items: list[dict], paper_id: str, valid_chunk_ids: set[str]) -> list[Interpretation]:
        out: list[Interpretation] = []
        for idx, item in enumerate(items):
            evidence = self._valid_evidence(item.get("evidence_chunk_ids", []), valid_chunk_ids)
            if not evidence:
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            out.append(
                Interpretation(
                    interpretation_id=item.get("interpretation_id") or f"{paper_id}_interp_{idx}",
                    paper_id=paper_id,
                    text=text,
                    evidence_chunk_ids=evidence,
                    confidence=_clamp_conf(item.get("confidence", 0.65)),
                )
            )
        return out

    def _parse_results(self, items: list[dict], paper_id: str, valid_chunk_ids: set[str]) -> list[ResultRecord]:
        out: list[ResultRecord] = []
        for idx, item in enumerate(items):
            evidence = self._valid_evidence(item.get("source_chunk_ids", []), valid_chunk_ids)
            if not evidence:
                continue
            try:
                value = float(item.get("value"))
            except (TypeError, ValueError):
                continue
            out.append(
                ResultRecord(
                    result_id=item.get("result_id") or f"{paper_id}_result_{idx}",
                    paper_id=paper_id,
                    table_id=item.get("table_id"),
                    source_reference=item.get("source_reference"),
                    dataset=str(item.get("dataset", "unknown")),
                    split=str(item.get("split", "unknown")),
                    method=str(item.get("method", "unknown")),
                    baseline=item.get("baseline"),
                    metric=str(item.get("metric", "unknown")),
                    value=value,
                    unit=item.get("unit") or "points",
                    source_chunk_ids=evidence,
                )
            )
        return out

    def _valid_evidence(self, evidence_ids: list[str], valid_chunk_ids: set[str]) -> list[str]:
        evidence = [e for e in evidence_ids if e in valid_chunk_ids]
        return list(dict.fromkeys(evidence))


def _clamp_conf(value: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, x))
