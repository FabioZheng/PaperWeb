"""Multi-source connectors for latest-paper discovery."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import date
from typing import Any

import httpx

from app.models import PaperMetadata

LOGGER = logging.getLogger(__name__)

DEFAULT_HTTP_HEADERS = {
    "User-Agent": "PaperWeb/0.1 (+https://github.com/)"
}


class PaperSourceConnector(ABC):
    name: str

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 20,
        from_date: date | None = None,
        to_date: date | None = None,
        fields: list[str] | None = None,
    ) -> list[PaperMetadata]:
        """Search papers and return normalized metadata."""


class ArxivConnector(PaperSourceConnector):
    name = "arxiv"

    def search(self, query: str, limit: int = 20, from_date: date | None = None, to_date: date | None = None, fields: list[str] | None = None) -> list[PaperMetadata]:
        candidates = _arxiv_query_candidates(query or "")
        q = candidates[0]
        url = "https://export.arxiv.org/api/query"
        out: list[PaperMetadata] = []
        for q in candidates:
            params = {
                "search_query": q,
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            text = httpx.get(url, params=params, timeout=30.0).text
            items = text.split("<entry>")[1:]
            out = []
            for entry in items:
                arxiv_id = _between(entry, "<id>", "</id>").split("/")[-1]
                title = _clean(_between(entry, "<title>", "</title>"))
                abstract = _clean(_between(entry, "<summary>", "</summary>"))
                published = _between(entry, "<published>", "</published>")[:10] or None
                updated = _between(entry, "<updated>", "</updated>")[:10] or published
                authors = [_clean(v) for v in _all_between(entry, "<name>", "</name>")]
                pdf_url = _find_pdf_url(entry, arxiv_id)
                out.append(
                    PaperMetadata(
                        paper_id=f"arxiv:{arxiv_id}",
                        source=self.name,
                        source_url=f"https://arxiv.org/abs/{arxiv_id}",
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        published_date=published,
                        updated_date=updated,
                        venue="arXiv",
                        year=int(published[:4]) if published else None,
                        arxiv_id=arxiv_id,
                        pdf_url=pdf_url,
                        topics=[],
                        raw_source_payload={"entry": entry[:2000]},
                    )
                )
            if out:
                return out
        return out


class OpenAlexConnector(PaperSourceConnector):
    name = "openalex"

    def search(self, query: str, limit: int = 20, from_date: date | None = None, to_date: date | None = None, fields: list[str] | None = None) -> list[PaperMetadata]:
        filter_parts = []
        if from_date:
            filter_parts.append(f"from_publication_date:{from_date.isoformat()}")
        if to_date:
            filter_parts.append(f"to_publication_date:{to_date.isoformat()}")
        params: dict[str, Any] = {
            "search": query,
            "per-page": limit,
        }
        if filter_parts:
            params["filter"] = ",".join(filter_parts)
        mailto = os.getenv("OPENALEX_MAILTO")
        if mailto:
            params["mailto"] = mailto
        data = _get_json_dict("https://api.openalex.org/works", params=params)
        out: list[PaperMetadata] = []
        for item in data.get("results", []):
            openalex_id = str(item.get("id", "")).split("/")[-1] or None
            doi = item.get("doi")
            cited_by = item.get("cited_by_count")
            counts_by_year = item.get("counts_by_year") or []
            out.append(
                PaperMetadata(
                    paper_id=f"openalex:{openalex_id or _hash_title(item.get('title',''))}",
                    source=self.name,
                    source_url=item.get("id"),
                    title=item.get("title") or "",
                    abstract=_openalex_abstract(item.get("abstract_inverted_index")),
                    authors=[a.get("author", {}).get("display_name") for a in item.get("authorships", []) if a.get("author")],
                    published_date=item.get("publication_date"),
                    updated_date=item.get("updated_date", "")[:10] or item.get("publication_date"),
                    venue=(item.get("primary_location", {}) or {}).get("source", {}).get("display_name"),
                    year=item.get("publication_year"),
                    doi=doi,
                    arxiv_id=(item.get("ids", {}) or {}).get("arxiv"),
                    openalex_id=openalex_id,
                    pdf_url=(item.get("primary_location", {}) or {}).get("pdf_url"),
                    citation_count=cited_by,
                    fields_of_study=[c.get("display_name") for c in item.get("concepts", []) if c.get("display_name")],
                    reference_count=item.get("referenced_works_count"),
                    influential_citation_count=(counts_by_year[0].get("cited_by_count") if counts_by_year else None),
                    raw_source_payload=item,
                )
            )
        return out


class SemanticScholarConnector(PaperSourceConnector):
    name = "semantic_scholar"

    def search(self, query: str, limit: int = 20, from_date: date | None = None, to_date: date | None = None, fields: list[str] | None = None) -> list[PaperMetadata]:
        req_fields = fields or [
            "paperId,title,abstract,authors,year,venue,url,externalIds,openAccessPdf,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationDate"
        ]
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        candidates = _semantic_scholar_query_candidates(query)
        data = {}
        for q in candidates:
            params = {"query": q, "limit": limit, "fields": req_fields[0]}
            data = _get_json_dict(url, params=params)
            if data.get("data"):
                break
        out: list[PaperMetadata] = []
        for item in data.get("data", []):
            ext = item.get("externalIds") or {}
            out.append(
                PaperMetadata(
                    paper_id=f"semanticscholar:{item.get('paperId')}",
                    source=self.name,
                    source_url=item.get("url"),
                    title=item.get("title") or "",
                    abstract=item.get("abstract"),
                    authors=[a.get("name") for a in item.get("authors", []) if a.get("name")],
                    published_date=item.get("publicationDate"),
                    updated_date=item.get("publicationDate"),
                    venue=item.get("venue"),
                    year=item.get("year"),
                    doi=ext.get("DOI"),
                    arxiv_id=ext.get("ArXiv"),
                    semantic_scholar_id=item.get("paperId"),
                    pdf_url=(item.get("openAccessPdf") or {}).get("url"),
                    citation_count=item.get("citationCount"),
                    reference_count=item.get("referenceCount"),
                    influential_citation_count=item.get("influentialCitationCount"),
                    fields_of_study=item.get("fieldsOfStudy") or [],
                    raw_source_payload=item,
                )
            )
        return out


def _clean(value: str) -> str:
    return " ".join((value or "").split())


def _between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        return ""
    return text.split(start, 1)[1].split(end, 1)[0]


def _all_between(text: str, start: str, end: str) -> list[str]:
    parts = text.split(start)[1:]
    return [p.split(end, 1)[0] for p in parts if end in p]


def _hash_title(title: str) -> str:
    return hashlib.md5(title.lower().strip().encode()).hexdigest()[:12]


def _find_pdf_url(entry: str, arxiv_id: str) -> str:
    marker = 'title="pdf" href="'
    if marker in entry:
        return entry.split(marker, 1)[1].split('"', 1)[0]
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def _openalex_abstract(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    inv: dict[int, str] = {}
    for word, positions in index.items():
        for p in positions:
            inv[p] = word
    return " ".join(inv[p] for p in sorted(inv))


def _get_json_dict(url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = httpx.get(url, params=params, headers=DEFAULT_HTTP_HEADERS, timeout=30.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {url}, got {type(payload).__name__}")
    return payload


def _arxiv_query_candidates(raw: str) -> list[str]:
    q = raw.strip()
    if not q:
        return ["cat:cs.CL"]
    terms = [t.strip() for t in re.split(r"\bOR\b", q, flags=re.IGNORECASE) if t.strip()]
    candidates = [q]
    if terms:
        candidates.append(" OR ".join(f'all:\"{t}\"' for t in terms))
        candidates.append("all:" + " ".join(terms))
        candidates.append(" OR ".join(f"ti:{t}" for t in terms))
    candidates.append("cat:cs.IR OR cat:cs.CL")
    return list(dict.fromkeys(candidates))


def _semantic_scholar_query_candidates(raw: str) -> list[str]:
    q = raw.strip()
    if not q:
        return [q]
    relaxed = re.sub(r"\b(AND|OR|NOT)\b", " ", q, flags=re.IGNORECASE)
    relaxed = " ".join(relaxed.split())
    return list(dict.fromkeys([q, relaxed]))
