"""Structured metadata and extraction persistence in SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models import ExtractedMemory, PaperMetadata, ParsedChunk


class StructuredDB:
    def __init__(self, path: str = "data/paperweb.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS papers (paper_id TEXT PRIMARY KEY, payload TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS chunks (chunk_id TEXT PRIMARY KEY, paper_id TEXT, payload TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS extracted (paper_id TEXT PRIMARY KEY, payload TEXT)")
        self.conn.commit()

    def upsert_paper(self, paper: PaperMetadata) -> None:
        self.conn.execute(
            "REPLACE INTO papers (paper_id, payload) VALUES (?, ?)",
            (paper.paper_id, json.dumps(paper.model_dump())),
        )
        self.conn.commit()

    def upsert_chunks(self, chunks: list[ParsedChunk]) -> None:
        self.conn.executemany(
            "REPLACE INTO chunks (chunk_id, paper_id, payload) VALUES (?, ?, ?)",
            [(c.chunk_id, c.paper_id, json.dumps(c.model_dump())) for c in chunks],
        )
        self.conn.commit()

    def upsert_extracted(self, paper_id: str, memory: ExtractedMemory) -> None:
        self.conn.execute("REPLACE INTO extracted (paper_id, payload) VALUES (?, ?)", (paper_id, memory.model_dump_json()))
        self.conn.commit()
