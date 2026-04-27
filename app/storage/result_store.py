"""Structured numeric result store for exact filtering/ranking."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.models import ResultRecord, RetrievedItem


@dataclass
class ResultStore:
    results: list[ResultRecord] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str = "data/result_store.json") -> "ResultStore":
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text())
        return cls(results=[ResultRecord.model_validate(r) for r in data])

    def save(self, path: str = "data/result_store.json") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([r.model_dump() for r in self.results], indent=2))

    def add_many(self, records: list[ResultRecord]) -> None:
        self.results.extend(records)

    def query(self, dataset: str | None = None, metric: str | None = None, top_k: int = 5) -> list[RetrievedItem]:
        records = self.results
        if dataset:
            records = [r for r in records if r.dataset.lower() == dataset.lower()]
        if metric:
            records = [r for r in records if r.metric.lower() == metric.lower()]
        records = sorted(records, key=lambda r: r.value, reverse=True)[:top_k]
        return [
            RetrievedItem(
                item_id=r.result_id,
                source_store="result",
                text=f"{r.method} {r.metric}={r.value} on {r.dataset} {r.split}",
                score=r.value / 100.0,
                provenance={"paper_id": r.paper_id, "source_chunk_ids": r.source_chunk_ids},
            )
            for r in records
        ]
