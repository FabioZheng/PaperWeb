from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from app.intelligence.schema import IntelligencePaper

STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "using", "based", "study", "paper", "approach", "model"}


@dataclass
class TopicBucket:
    topic_id: str
    title: str
    description: str
    inclusion_criteria: str
    exclusion_criteria: str
    aliases: list[str] = field(default_factory=list)


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{4,}", text.lower()) if t not in STOP]


def build_topic_taxonomy(
    papers: list[IntelligencePaper],
    k: int,
    field: str,
    llm_provider: str | None = None,
) -> list[TopicBucket]:
    # deterministic fallback: abstracts-only keyword grouping
    corpus = " ".join((p.abstract or "") for p in papers)
    common = [w for w, _ in Counter(_tokens(corpus)).most_common(max(k * 4, k))]
    buckets: list[TopicBucket] = []
    for i in range(k):
        seed = common[i] if i < len(common) else f"theme_{i+1}"
        buckets.append(
            TopicBucket(
                topic_id=f"T{i+1:02d}",
                title=seed.replace("_", " ").title(),
                description=f"{field} direction centered on abstract signals around '{seed}'.",
                inclusion_criteria=f"Abstract mentions '{seed}' or closely related terms.",
                exclusion_criteria=f"Abstract not materially connected to '{seed}'.",
                aliases=[seed],
            )
        )
    return buckets


def save_taxonomy_json(taxonomy: list[TopicBucket], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(t) for t in taxonomy], f, indent=2)


def load_taxonomy_json(path: str) -> list[TopicBucket]:
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    return [TopicBucket(**r) for r in rows]
