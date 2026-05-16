from __future__ import annotations

import json
import sqlite3

from app.paper_cards.schema import PaperCard


class PaperCardStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.execute("CREATE TABLE IF NOT EXISTS paper_cards (paper_id TEXT PRIMARY KEY, payload TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS paper_card_acronyms (paper_id TEXT, acronym TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS paper_card_terms (paper_id TEXT, term TEXT)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pca_acronym ON paper_card_acronyms(acronym)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pct_term ON paper_card_terms(term)")
        self.conn.commit()

    def upsert(self, card: PaperCard) -> None:
        self.conn.execute("REPLACE INTO paper_cards (paper_id, payload) VALUES (?, ?)", (card.paper_id, json.dumps(card.model_dump())))
        self.conn.execute("DELETE FROM paper_card_acronyms WHERE paper_id = ?", (card.paper_id,))
        self.conn.execute("DELETE FROM paper_card_terms WHERE paper_id = ?", (card.paper_id,))
        self.conn.executemany("INSERT INTO paper_card_acronyms (paper_id, acronym) VALUES (?, ?)", [(card.paper_id, a) for a in card.acronyms])
        self.conn.executemany("INSERT INTO paper_card_terms (paper_id, term) VALUES (?, ?)", [(card.paper_id, t) for t in card.key_terms])
        self.conn.commit()

    def list_cards(self) -> list[PaperCard]:
        rows = self.conn.execute("SELECT payload FROM paper_cards").fetchall()
        return [PaperCard.model_validate_json(r[0]) for r in rows]
