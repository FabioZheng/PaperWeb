"""Topic consolidation job for machine memory + Obsidian notes."""

from __future__ import annotations

from collections import defaultdict

from app.models import PaperMetadata, TopicNote


class TopicConsolidator:
    def consolidate(self, papers: list[PaperMetadata]) -> list[TopicNote]:
        grouped: dict[str, list[PaperMetadata]] = defaultdict(list)
        for p in papers:
            for topic in p.topics:
                grouped[topic.lower()].append(p)

        notes: list[TopicNote] = []
        for idx, (topic, items) in enumerate(grouped.items()):
            summary = f"{len(items)} papers discuss {topic}. Focus: " + "; ".join(i.title for i in items[:3])
            notes.append(
                TopicNote(
                    topic_id=f"t{idx}",
                    topic_name=topic,
                    paper_ids=[i.paper_id for i in items],
                    summary=summary,
                )
            )
        return notes
