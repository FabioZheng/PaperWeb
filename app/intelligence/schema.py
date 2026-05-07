from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IntelligencePaper:
    paper_id: str
    title: str
    abstract: str = ""
    year: int | None = None
    venue: str = ""
    authors: list[str] = field(default_factory=list)
    institutions: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    fields_of_study: list[str] = field(default_factory=list)
    citation_count: int = 0
    influential_citation_count: int = 0
