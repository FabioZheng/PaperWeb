"""Deduplication, enrichment, and freshness tracking for paper metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.models import PaperMetadata


class PaperIdentityResolver:
    def identity_keys(self, paper: PaperMetadata) -> list[str]:
        keys: list[str] = []
        for label, value in [
            ("doi", paper.doi),
            ("arxiv", paper.arxiv_id),
            ("openreview", paper.openreview_id),
            ("semanticscholar", paper.semantic_scholar_id),
            ("openalex", paper.openalex_id),
        ]:
            if value:
                keys.append(f"{label}:{str(value).lower().strip()}")
        if not keys:
            keys.append(f"title:{self._norm_title(paper.title)}")
        return keys

    def _norm_title(self, title: str) -> str:
        return "".join(ch.lower() for ch in title if ch.isalnum() or ch.isspace()).strip()


class MetadataEnricher:
    def merge(self, base: PaperMetadata, candidate: PaperMetadata) -> PaperMetadata:
        merged = base.model_copy(deep=True)
        for field in type(base).model_fields:
            if field in {"source_seen_history", "raw_source_payload", "field_provenance"}:
                continue
            cur = getattr(merged, field)
            nxt = getattr(candidate, field)
            if self._prefer_new(cur, nxt):
                setattr(merged, field, nxt)
                merged.field_provenance[field] = candidate.source

        merged.raw_source_payload[candidate.source] = candidate.raw_source_payload
        if candidate.source not in merged.source_seen_history:
            merged.source_seen_history.append(candidate.source)
        merged.topics = sorted(set((merged.topics or []) + (candidate.topics or [])))
        merged.fields_of_study = sorted(set((merged.fields_of_study or []) + (candidate.fields_of_study or [])))
        return merged

    def _prefer_new(self, cur, nxt) -> bool:
        if nxt is None:
            return False
        if cur is None:
            return True
        if isinstance(cur, str) and isinstance(nxt, str):
            return len(nxt.strip()) > len(cur.strip())
        if isinstance(cur, list) and isinstance(nxt, list):
            return len(nxt) > len(cur)
        if isinstance(cur, int) and isinstance(nxt, int):
            return nxt > cur
        return False


@dataclass
class DedupResult:
    papers: list[PaperMetadata]
    duplicates_merged: int


class PaperDeduplicator:
    def __init__(self):
        self.resolver = PaperIdentityResolver()
        self.enricher = MetadataEnricher()

    def deduplicate(self, papers: list[PaperMetadata]) -> DedupResult:
        by_key: dict[str, PaperMetadata] = {}
        out: list[PaperMetadata] = []
        merged = 0
        for paper in papers:
            keys = self.resolver.identity_keys(paper)
            found = None
            for key in keys:
                if key in by_key:
                    found = by_key[key]
                    break
            if not found:
                out.append(paper)
                for key in keys:
                    by_key[key] = paper
                continue
            merged_paper = self.enricher.merge(found, paper)
            for i, p in enumerate(out):
                if p is found:
                    out[i] = merged_paper
                    break
            for key in keys + self.resolver.identity_keys(merged_paper):
                by_key[key] = merged_paper
            merged += 1
        return DedupResult(papers=out, duplicates_merged=merged)


class FreshnessTracker:
    def __init__(self, path: str = "data/paper_index.json"):
        self.path = Path(path)
        self.index = self._load()

    def apply(self, papers: list[PaperMetadata]) -> tuple[list[PaperMetadata], int, int]:
        now = datetime.now(UTC).isoformat()
        new_count = 0
        updated_count = 0
        out: list[PaperMetadata] = []
        for paper in papers:
            key = self._paper_key(paper)
            metadata_hash = self._hash_metadata(paper)
            pdf_hash = self._hash_text(paper.pdf_url)
            prev = self.index.get(key)
            if not prev:
                paper.first_seen_at = now
                paper.last_seen_at = now
                paper.version = 1
                paper.metadata_hash = metadata_hash
                paper.pdf_hash = pdf_hash
                paper.is_new = True
                paper.is_updated = False
                new_count += 1
            else:
                paper.first_seen_at = prev.get("first_seen_at")
                paper.last_seen_at = now
                paper.version = int(prev.get("version", 1))
                changed = prev.get("metadata_hash") != metadata_hash or prev.get("pdf_hash") != pdf_hash
                if changed:
                    paper.version += 1
                    paper.is_updated = True
                    updated_count += 1
                else:
                    paper.is_updated = False
                paper.is_new = False
                paper.metadata_hash = metadata_hash
                paper.pdf_hash = pdf_hash
                prior_sources = prev.get("source_seen_history", [])
                paper.source_seen_history = sorted(set((paper.source_seen_history or []) + prior_sources))

            self.index[key] = {
                "first_seen_at": paper.first_seen_at,
                "last_seen_at": paper.last_seen_at,
                "version": paper.version,
                "metadata_hash": paper.metadata_hash,
                "pdf_hash": paper.pdf_hash,
                "source_seen_history": paper.source_seen_history,
            }
            out.append(paper)
        self._save()
        return out, new_count, updated_count

    def _paper_key(self, paper: PaperMetadata) -> str:
        for v in [paper.doi, paper.arxiv_id, paper.openreview_id, paper.semantic_scholar_id, paper.openalex_id]:
            if v:
                return str(v).lower()
        return paper.title.lower().strip()

    def _hash_metadata(self, paper: PaperMetadata) -> str:
        payload = paper.model_dump(exclude={"first_seen_at", "last_seen_at", "is_new", "is_updated", "version"})
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    def _hash_text(self, value: str | None) -> str | None:
        if not value:
            return None
        return hashlib.sha256(value.encode()).hexdigest()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.index, indent=2, ensure_ascii=False), encoding="utf-8")
