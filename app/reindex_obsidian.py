"""CLI to re-index Obsidian notes into vector store."""

from __future__ import annotations

from app.obsidian.notes import ObsidianService
from app.storage.vector_store import VectorStore


def main() -> None:
    store = VectorStore.from_file()
    count = ObsidianService().reindex_notes(store)
    store.save()
    print(f"Reindexed {count} notes")


if __name__ == "__main__":
    main()
