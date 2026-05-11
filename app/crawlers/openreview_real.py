"""Production crawler using the arXiv API + PDF downloads."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

import httpx

from app.crawlers.base import ConferenceCrawler
from app.models import PaperMetadata
from app.net import tls_verify_enabled

ARXIV_ATOM_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}

FIELD_TO_QUERY = {
    "nlp": "cat:cs.CL",
    "cv": "cat:cs.CV",
    "ml": "cat:cs.LG",
    "ai": "cat:cs.AI",
    "robotics": "cat:cs.RO",
    "all": "cat:cs.CL OR cat:cs.CV OR cat:cs.LG OR cat:cs.AI",
}


class OpenReviewRealCrawler(ConferenceCrawler):
    """Fetches papers from arXiv and stores local PDFs."""

    def __init__(
        self,
        query: str | None = None,
        research_field: str = "nlp",
        paper_type: str = "recent",
        pdf_dir: str = "data/pdfs",
        timeout_s: float = 30.0,
    ):
        self.query = self._build_query(query=query, research_field=research_field, paper_type=paper_type)
        self.research_field = research_field
        self.paper_type = paper_type
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_s = timeout_s

    def fetch_recent(self, limit: int) -> list[PaperMetadata]:
        if limit <= 0:
            return []
        feed_xml = self._fetch_arxiv_feed(limit)
        root = ET.fromstring(feed_xml)
        papers: list[PaperMetadata] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = self._entry_to_paper(entry)
            if paper:
                papers.append(paper)
            if len(papers) >= limit:
                break
        return papers

    def _build_query(self, query: str | None, research_field: str, paper_type: str) -> str:
        if query:
            return query
        field_query = FIELD_TO_QUERY.get(research_field.lower(), FIELD_TO_QUERY["all"])
        normalized_type = paper_type.strip().lower()
        if normalized_type in {"recent", "latest", "all"}:
            return field_query
        # paper_type is treated as keyword constraint over title/abstract
        return f"({field_query}) AND all:{normalized_type}"

    def _fetch_arxiv_feed(self, limit: int) -> str:
        params = {
            "search_query": self.query,
            "start": "0",
            "max_results": str(limit),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        query = "&".join(f"{k}={quote(v)}" for k, v in params.items())
        url = f"{ARXIV_ATOM_URL}?{query}"
        with httpx.Client(timeout=self.timeout_s, follow_redirects=True, verify=tls_verify_enabled()) as client:
            for attempt in range(4):
                response = client.get(url, headers={"User-Agent": "paperweb/0.1 (+https://example.org)"})
                if response.status_code != 429:
                    response.raise_for_status()
                    return response.text
                retry_after = response.headers.get("Retry-After")
                wait_s = float(retry_after) if retry_after and retry_after.isdigit() else (1.5 * (attempt + 1))
                time.sleep(wait_s)
        raise RuntimeError("arXiv API rate-limited (HTTP 429) after retries; please retry in a minute or lower request frequency.")

    def _entry_to_paper(self, entry: ET.Element) -> PaperMetadata | None:
        paper_id_raw = _text(entry.find("atom:id", ARXIV_NS))
        if not paper_id_raw:
            return None
        paper_id = _normalize_paper_id(paper_id_raw)
        title = _text(entry.find("atom:title", ARXIV_NS))
        abstract = _text(entry.find("atom:summary", ARXIV_NS))
        authors = [a for a in (_text(n.find("atom:name", ARXIV_NS)) for n in entry.findall("atom:author", ARXIV_NS)) if a]

        published = _text(entry.find("atom:published", ARXIV_NS))
        accepted_date = published[:10] if published else datetime.now(UTC).strftime("%Y-%m-%d")
        year = int(accepted_date[:4])

        categories = self._collect_categories(entry)
        venue = "arXiv"
        source_url = paper_id_raw
        pdf_url = self._find_pdf_url(entry, paper_id)
        pdf_path = self._download_pdf(paper_id, pdf_url)

        topics = categories if categories else [self.research_field]
        if self.paper_type.lower() not in {"recent", "latest", "all"}:
            topics = [*topics, self.paper_type.lower()]

        return PaperMetadata(
            paper_id=paper_id,
            title=title or paper_id,
            authors=authors or ["Unknown"],
            venue=venue,
            year=year,
            accepted_date=accepted_date,
            abstract=abstract,
            source_url=source_url,
            pdf_path=str(pdf_path),
            topics=topics[:6],
        )

    def _collect_categories(self, entry: ET.Element) -> list[str]:
        cats: list[str] = []
        for cat in entry.findall("atom:category", ARXIV_NS):
            term = cat.attrib.get("term", "").strip()
            if term and term not in cats:
                cats.append(term)
        return cats[:5]

    def _find_pdf_url(self, entry: ET.Element, paper_id: str) -> str:
        for link in entry.findall("atom:link", ARXIV_NS):
            if link.attrib.get("title") == "pdf" and link.attrib.get("href"):
                return link.attrib["href"]
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    def _download_pdf(self, paper_id: str, pdf_url: str) -> Path:
        pdf_path = self.pdf_dir / f"{paper_id}.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return pdf_path

        with httpx.Client(timeout=self.timeout_s, follow_redirects=True, verify=tls_verify_enabled()) as client:
            response = client.get(pdf_url, headers={"User-Agent": "paperweb/0.1 (+https://example.org)"})
            response.raise_for_status()
            pdf_path.write_bytes(response.content)
        return pdf_path


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return " ".join(node.text.split())


def _normalize_paper_id(arxiv_id_url: str) -> str:
    tail = arxiv_id_url.rstrip("/").split("/")[-1]
    normalized = re.sub(r"[^a-zA-Z0-9_.-]", "_", tail)
    return normalized
