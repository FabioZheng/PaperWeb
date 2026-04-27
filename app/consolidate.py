"""CLI to regenerate topic notes from fixture papers."""

from __future__ import annotations

import json

from app.consolidation.topic_consolidator import TopicConsolidator
from app.models import PaperMetadata
from app.obsidian.notes import ObsidianService


def main() -> None:
    papers = [PaperMetadata.model_validate(p) for p in json.loads(open("fixtures/papers/mock_papers.json").read())]
    notes = TopicConsolidator().consolidate(papers)
    obsidian = ObsidianService()
    for n in notes:
        obsidian.write_topic_note(n)


if __name__ == "__main__":
    main()
