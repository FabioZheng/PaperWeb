"""CLI to re-index Obsidian notes into vector store."""

from __future__ import annotations

import sys

from app.cli import print_cli_banner
from app.obsidian.notes import ObsidianService
from app.storage.vector_store import VectorStore


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    print_cli_banner()
    store = VectorStore.from_file()
    count = ObsidianService().reindex_notes(store)
    store.save()
    print(f"Reindexed {count} notes")


if __name__ == "__main__":
    main()
