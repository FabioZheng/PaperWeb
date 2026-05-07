"""CLI to regenerate topic notes from fixture papers."""

from __future__ import annotations

from app.cli import print_cli_banner
import json

from app.consolidation.topic_consolidator import TopicConsolidator
from app.models import PaperMetadata
from app.obsidian.notes import ObsidianService


def main() -> None:
    print_cli_banner()
    papers = [PaperMetadata.model_validate(p) for p in json.loads(open("fixtures/papers/mock_papers.json").read())]
    notes = TopicConsolidator().consolidate(papers)
    obsidian = ObsidianService()
    for n in notes:
        obsidian.write_topic_note(n)


if __name__ == "__main__":
    main()
