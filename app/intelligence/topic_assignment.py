from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from app.extraction.llm_provider import build_provider
from app.intelligence.schema import IntelligencePaper
from app.intelligence.taxonomy import TopicBucket


@dataclass
class TopicAssignment:
    paper_id: str
    primary_topic_id: str
    secondary_topic_ids: list[str] = field(default_factory=list)
    fit_score: float = 0.0
    reason: str = ""
    other_topic_title: str = ""


def _tok(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", (text or "").lower()))


def assign_papers_to_taxonomy(
    papers: list[IntelligencePaper],
    taxonomy: list[TopicBucket],
    llm_provider: str | None = None,
    min_fit_score: float = 0.45,
) -> list[TopicAssignment]:
    if llm_provider:
        _ = build_provider("topic_extractor")
    assignments: list[TopicAssignment] = []
    for p in papers:
        atok = _tok(p.abstract)
        scored: list[tuple[str, float, str]] = []
        for t in taxonomy:
            tset = _tok(" ".join([t.title, t.description, " ".join(t.aliases), t.inclusion_criteria]))
            if not atok or not tset:
                score = 0.0
            else:
                score = len(atok & tset) / max(1, len(atok | tset))
            scored.append((t.topic_id, score, t.title))
        scored.sort(key=lambda x: x[1], reverse=True)
        best_id, best_score, best_title = scored[0] if scored else ("OTHER", 0.0, "")
        secondaries = [sid for sid, s, _ in scored[1:3] if s >= min_fit_score + 0.15]
        if best_score < min_fit_score:
            keyword = sorted(atok)[:2]
            other_title = " ".join(keyword).title() if keyword else "Unclear abstract topic"
            assignments.append(TopicAssignment(p.paper_id, "OTHER", secondaries, best_score, "Low taxonomy fit from abstract-only match", other_title))
        else:
            assignments.append(TopicAssignment(p.paper_id, best_id, secondaries, best_score, f"Matched abstract terms to topic '{best_title}'", ""))
    return assignments


def save_assignments_json(assignments: list[TopicAssignment], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(a) for a in assignments], f, indent=2, ensure_ascii=False)
