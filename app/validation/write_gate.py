"""Strict write-gate validation before memory persistence."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Entity, ExtractedMemory, ParsedChunk
from app.normalization.entity_normalizer import EntityNormalizer


@dataclass
class WriteGate:
    normalizer: EntityNormalizer

    def validate_and_prepare(
        self,
        extracted: ExtractedMemory,
        chunks: list[ParsedChunk],
        entities: list[Entity],
    ) -> tuple[ExtractedMemory, list[Entity]]:
        chunk_ids = {c.chunk_id for c in chunks}

        def _ensure_evidence(ids: list[str]) -> None:
            if not ids or not set(ids).issubset(chunk_ids):
                raise ValueError(f"Invalid evidence references: {ids}")

        for item in extracted.facts:
            _ensure_evidence(item.evidence_chunk_ids)
        for item in extracted.claims:
            _ensure_evidence(item.evidence_chunk_ids)
        for item in extracted.interpretations:
            _ensure_evidence(item.evidence_chunk_ids)
        for item in extracted.results:
            _ensure_evidence(item.source_chunk_ids)

        dedup_claims = {c.text: c for c in extracted.claims}
        extracted.claims = list(dedup_claims.values())

        normalized_entities = [self.normalizer.normalize_entity(e) for e in entities]
        return extracted, normalized_entities
