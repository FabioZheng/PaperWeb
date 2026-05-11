"""Obsidian markdown generation and re-indexing."""

from __future__ import annotations

from pathlib import Path

from app.models import PaperMetadata, TopicNote
from app.storage.vector_store import VectorStore


class ObsidianService:
    def __init__(self, vault_dir: str = "fixtures/obsidian_vault"):
        self.vault = Path(vault_dir)
        self.vault.mkdir(parents=True, exist_ok=True)

    def write_paper_note(self, paper: PaperMetadata, summary: str) -> Path:
        path = self.vault / f"paper_{paper.paper_id}.md"
        tags = " ".join(f"#{t.replace(' ', '_')}" for t in paper.topics)
        path.write_text(
            f"# {paper.title}\n\n- Venue: {paper.venue} ({paper.year})\n- Authors: {', '.join(paper.authors)}\n- Tags: {tags}\n\n## Summary\n{summary}\n"
        , encoding="utf-8")
        return path

    def write_topic_note(self, topic: TopicNote) -> Path:
        path = self.vault / f"topic_{topic.topic_id}.md"
        links = "\n".join([f"- [[paper_{pid}]]" for pid in topic.paper_ids])
        path.write_text(f"# Topic: {topic.topic_name}\n\n{topic.summary}\n\n## Papers\n{links}\n", encoding="utf-8")
        return path

    def reindex_notes(self, vector_store: VectorStore) -> int:
        count = 0
        for note in self.vault.glob("*.md"):
            vector_store.add(
                item_id=f"obsidian_{note.stem}",
                text=note.read_text(encoding="utf-8", errors="replace"),
                metadata={"path": str(note)},
                curated=True,
            )
            count += 1
        return count
