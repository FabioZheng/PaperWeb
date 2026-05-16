from __future__ import annotations

from pydantic import BaseModel, Field


class PaperCard(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    source: str = "unknown"
    abstract: str | None = None
    full_text_path: str | None = None
    field: str | None = None
    key_terms: list[str] = Field(default_factory=list)
    acronyms: list[str] = Field(default_factory=list)
    problem: str | None = None
    method: str | None = None
    contribution: str | None = None
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    results: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_spans: list[str] = Field(default_factory=list)
