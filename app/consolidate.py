"""CLI to regenerate topic notes from fixture papers."""

from __future__ import annotations

from app.cli import print_cli_banner
import json
import sys

from app.consolidation.topic_consolidator import TopicConsolidator
from app.models import PaperMetadata
from app.obsidian.notes import ObsidianService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    print_cli_banner()
    papers = [PaperMetadata.model_validate(p) for p in json.loads(open("fixtures/papers/mock_papers.json", encoding="utf-8", errors="replace").read())]
    notes = TopicConsolidator().consolidate(papers)
    obsidian = ObsidianService()
    for n in notes:
        obsidian.write_topic_note(n)


if __name__ == "__main__":
    main()
