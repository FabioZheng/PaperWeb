"""Typed schemas for the research-memory pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SupportType(str, Enum):
    EXPLICIT = "explicit"
    TABLE_DERIVED = "table_derived"
    LLM_INFERRED = "llm_inferred"


class PaperMetadata(BaseModel):
    paper_id: str
    source: str = "unknown"
    source_url: str | None = None
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_date: str | None = None
    updated_date: str | None = None
    venue: str | None = None
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openreview_id: str | None = None
    semantic_scholar_id: str | None = None
    openalex_id: str | None = None
    pdf_url: str | None = None
    pdf_path: str = ""
    citation_count: int | None = None
    reference_count: int | None = None
    influential_citation_count: int | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    code_url: str | None = None
    raw_source_payload: dict[str, Any] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)

    # freshness/version tracking
    source_seen_history: list[str] = Field(default_factory=list)
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    version: int = 1
    metadata_hash: str | None = None
    pdf_hash: str | None = None
    is_new: bool = False
    is_updated: bool = False
    field_provenance: dict[str, str] = Field(default_factory=dict)

    # backward compatibility alias from prior fixtures
    accepted_date: str | None = None


class ParsedChunk(BaseModel):
    chunk_id: str
    paper_id: str
    section: str
    chunk_type: str
    text: str
    page_start: int
    page_end: int


class ExtractedFact(BaseModel):
    fact_id: str
    paper_id: str
    text: str
    evidence_chunk_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedClaim(BaseModel):
    claim_id: str
    paper_id: str
    claim_type: str
    text: str
    evidence_chunk_ids: list[str]
    support_type: SupportType
    confidence: float = Field(ge=0.0, le=1.0)


class Interpretation(BaseModel):
    interpretation_id: str
    paper_id: str
    text: str
    evidence_chunk_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ResultRecord(BaseModel):
    result_id: str
    paper_id: str
    table_id: str | None = None
    source_reference: str | None = None
    dataset: str
    split: str
    method: str
    baseline: str | None = None
    metric: str
    value: float
    unit: str | None = None
    source_chunk_ids: list[str]


class Entity(BaseModel):
    entity_id: str
    canonical_name: str
    aliases: list[str]
    entity_type: str


class Relation(BaseModel):
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    evidence_chunk_ids: list[str] = Field(default_factory=list)


class TopicNote(BaseModel):
    topic_id: str
    topic_name: str
    paper_ids: list[str]
    summary: str


class RouterPlan(BaseModel):
    intent: str
    entities: list[str]
    filters: dict[str, Any]
    store_weights: dict[str, float]
    retrieval_budget: dict[str, int]
    response_mode: str


class RetrievedItem(BaseModel):
    item_id: str
    source_store: str
    text: str
    score: float
    provenance: dict[str, Any]
    curated: bool = False


class EvidencePack(BaseModel):
    query: str
    plan: RouterPlan
    items: list[RetrievedItem]


class GeneratedAnswer(BaseModel):
    query: str
    answer: str
    citations: list[str]
    mode: str


class ExtractedMemory(BaseModel):
    facts: list[ExtractedFact]
    claims: list[ExtractedClaim]
    interpretations: list[Interpretation]
    results: list[ResultRecord]

    @model_validator(mode="after")
    def has_any_records(self) -> "ExtractedMemory":
        if not any((self.facts, self.claims, self.interpretations, self.results)):
            raise ValueError("At least one extracted record is required.")
        return self
