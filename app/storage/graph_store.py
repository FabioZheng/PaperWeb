"""SQLite-backed semantic graph for nodes, edges, and basic queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class GraphStore:
    def __init__(self, path: str = "data/paperweb.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS graph_nodes (node_id TEXT PRIMARY KEY, node_type TEXT, name TEXT)")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS graph_edges (edge_id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT, relation_type TEXT)"
        )
        self.conn.commit()

    def add_node(self, node_id: str, node_type: str, name: str) -> None:
        self.conn.execute("REPLACE INTO graph_nodes VALUES (?, ?, ?)", (node_id, node_type, name))
        self.conn.commit()

    def add_edge(self, edge_id: str, source_id: str, target_id: str, relation_type: str) -> None:
        self.conn.execute("REPLACE INTO graph_edges VALUES (?, ?, ?, ?)", (edge_id, source_id, target_id, relation_type))
        self.conn.commit()

    def papers_on_dataset(self, dataset: str) -> list[str]:
        q = """
        SELECT DISTINCT e.source_id FROM graph_edges e
        JOIN graph_nodes d ON d.node_id = e.target_id
        WHERE e.relation_type='EVALUATED_ON' AND d.name=?
        """
        return [r[0] for r in self.conn.execute(q, (dataset,)).fetchall()]

    def contradictions(self) -> list[tuple[str, str]]:
        q = "SELECT source_id, target_id FROM graph_edges WHERE relation_type='CONTRADICTS'"
        return self.conn.execute(q).fetchall()
