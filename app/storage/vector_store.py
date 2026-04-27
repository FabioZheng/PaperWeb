"""Simple local vector-like store with token-overlap scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.models import RetrievedItem


def _tokenize(text: str) -> set[str]:
    return {t.lower().strip(".,:;()[]") for t in text.split() if t.strip()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class VectorStore:
    entries: list[dict] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str = "data/vector_store.json") -> "VectorStore":
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text())
        store = cls(entries=data)
        for e in store.entries:
            e["tok"] = set(e.get("tok", []))
        return store

    def save(self, path: str = "data/vector_store.json") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for e in self.entries:
            serializable.append({**e, "tok": sorted(list(e["tok"]))})
        p.write_text(json.dumps(serializable, indent=2))

    def add(self, item_id: str, text: str, metadata: dict, curated: bool = False) -> None:
        self.entries.append({"item_id": item_id, "text": text, "tok": _tokenize(text), "metadata": metadata, "curated": curated})

    def search(self, query: str, limit: int = 5) -> list[RetrievedItem]:
        qtok = _tokenize(query)
        scored = []
        for e in self.entries:
            score = _jaccard(qtok, e["tok"])
            if e["curated"]:
                score += 0.1
            scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            RetrievedItem(
                item_id=e["item_id"],
                source_store="vector",
                text=e["text"],
                score=max(0.0, s),
                provenance=e["metadata"],
                curated=e["curated"],
            )
            for s, e in scored[:limit]
            if s > 0
        ]
