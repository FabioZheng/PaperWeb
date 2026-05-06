from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.intelligence.schema import IntelligencePaper


def load_intelligence_papers(db_path: str = "data/paperweb.db") -> list[IntelligencePaper]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT paper_id, payload FROM papers").fetchall()
    conn.close()
    papers: list[IntelligencePaper] = []
    for paper_id, payload in rows:
        try:
            data = json.loads(payload)
        except Exception:
            continue
        raw = data.get("raw_source_payload") or {}
        papers.append(
            IntelligencePaper(
                paper_id=paper_id,
                title=data.get("title") or paper_id,
                abstract=data.get("abstract") or "",
                year=data.get("year"),
                venue=data.get("venue") or "",
                authors=data.get("authors") or [],
                institutions=data.get("institutions") or _extract_institutions(raw),
                topics=data.get("topics") or [],
                fields_of_study=data.get("fields_of_study") or [],
                citation_count=int(data.get("citation_count") or 0),
                influential_citation_count=int(data.get("influential_citation_count") or 0),
            )
        )
    return papers


def _extract_institutions(raw: Any) -> list[str]:
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in {"institution", "institutions", "affiliation", "affiliations", "organization", "organizations"}:
                    if isinstance(v, str) and v.strip():
                        found.add(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                found.add(item.strip())
                            elif isinstance(item, dict):
                                name = item.get("name") or item.get("display_name")
                                if isinstance(name, str) and name.strip():
                                    found.add(name.strip())
                walk(v)
        elif isinstance(obj, list):
            for i in obj:
                walk(i)

    walk(raw)
    return sorted(found)
