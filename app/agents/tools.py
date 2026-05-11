from __future__ import annotations

import json
import sqlite3
from collections import Counter

from app.intelligence.loader import load_intelligence_papers
from app.intelligence.report import build_field_intelligence_report
from app.intelligence.taxonomy import build_topic_taxonomy
from app.intelligence.topic_assignment import assign_papers_to_taxonomy
from app.intelligence.topic_stats import compute_topic_direction_stats
from app.storage.graph_store import GraphStore
from app.storage.result_store import ResultStore
from app.storage.vector_store import VectorStore


def _conn(db_path: str):
    return sqlite3.connect(db_path)


def search_sql_metadata(query: str, filters: dict | None, db_path: str) -> dict:
    con = _conn(db_path)
    try:
        rows = con.execute("SELECT paper_id, payload FROM papers").fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    items = []
    q = query.lower()
    for pid, payload in rows:
        p = json.loads(payload)
        text = f"{p.get('title','')} {p.get('abstract','')} {' '.join(p.get('authors',[]))}".lower()
        if q in text:
            items.append({"paper_id": pid, "title": p.get("title"), "year": p.get("year")})
    return {"items": items[:20]}


def search_vector_store(query: str, top_k: int, db_path: str) -> dict:
    items = VectorStore.from_file(db_path.replace('.db', '_vector_store.json') if db_path.endswith('.db') else 'data/vector_store.json').search(query, limit=top_k)
    return {"items": [i.model_dump() for i in items]}


def search_graph_neighbors(entity: str, relation_type: str | None, db_path: str) -> dict:
    g = GraphStore(path=db_path)
    q = "SELECT source_id,target_id,relation_type FROM graph_edges WHERE source_id=? OR target_id=?"
    rows = g.conn.execute(q, (entity, entity)).fetchall()
    if relation_type:
        rows = [r for r in rows if r[2] == relation_type]
    return {"items": [{"source_id": r[0], "target_id": r[1], "relation_type": r[2]} for r in rows[:30]]}


def search_semantic_facts(query: str, top_k: int, db_path: str) -> dict:
    con = _conn(db_path)
    try:
        rows = con.execute("SELECT node_id,payload FROM graph_semantic").fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    q = query.lower()
    out = []
    for nid, payload in rows:
        if q in (payload or "").lower():
            out.append({"evidence_id": f"semantic:{nid}", "node_id": nid, "payload": payload[:500]})
    return {"items": out[:top_k]}


def get_paper_chunks(paper_id: str, db_path: str) -> dict:
    con = _conn(db_path)
    try:
        rows = con.execute("SELECT chunk_id,payload FROM chunks WHERE paper_id=?", (paper_id,)).fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    return {"items": [{"chunk_id": cid, **json.loads(payload)} for cid, payload in rows]}


def get_paper_facts(paper_id: str, db_path: str) -> dict:
    con = _conn(db_path)
    try:
        row = con.execute("SELECT payload FROM extracted WHERE paper_id=?", (paper_id,)).fetchone()
    except Exception:
        row = None
    finally:
        con.close()
    if not row:
        return {"items": []}
    payload = json.loads(row[0])
    facts = payload.get("facts", [])
    return {"items": [{"fact_id": f.get("fact_id"), "paper_id": paper_id, "text": f.get("text"), "evidence_chunk_ids": f.get("evidence_chunk_ids", [])} for f in facts]}


def get_topic_stats(field_or_topic: str, db_path: str) -> dict:
    try:
        papers = load_intelligence_papers(db_path)
    except Exception:
        papers = []
    if not papers:
        return {"items": []}
    taxonomy = build_topic_taxonomy(papers, k=6, field=field_or_topic)
    assignments = assign_papers_to_taxonomy(papers, taxonomy)
    stats = compute_topic_direction_stats(papers, taxonomy, assignments)
    return {"items": [s.__dict__ for s in stats[:10]]}


def run_field_intelligence(topic_or_field: str, db_path: str) -> dict:
    stats = get_topic_stats(topic_or_field, db_path).get("items", [])
    return {"items": stats, "summary": f"Computed {len(stats)} topic direction stats for {topic_or_field}."}


def generate_grounded_report(evidence: list[dict], db_path: str) -> dict:
    lines = ["# Grounded Report", ""]
    for i, e in enumerate(evidence, start=1):
        eid = e.get("fact_id") or e.get("chunk_id") or e.get("item_id") or e.get("evidence_id") or f"e{i}"
        lines.append(f"- [{eid}] {e.get('text', e.get('payload', ''))}")
    return {"report": "\n".join(lines), "evidence_ids": [e.get("fact_id") or e.get("chunk_id") or e.get("item_id") or e.get("evidence_id") for e in evidence]}
