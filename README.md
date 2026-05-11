# PaperWeb MVP: Research Memory Pipeline

PaperWeb is a production-oriented research-memory system for discovering papers, normalizing and storing paper intelligence, and answering grounded questions from retrieved evidence.

It currently supports two ingestion paths:
- **Legacy pipeline** (conference-style crawler → parse → extract → store).
- **Foundation multi-source ingestion** (arXiv/OpenAlex/Semantic Scholar connectors → dedup/enrichment/freshness tracking → canonical paper records).

---

## Table of contents

1. [What PaperWeb does](#what-paperweb-does)
2. [System architecture](#system-architecture)
3. [Pipeline tree (high-level)](#pipeline-tree-high-level)
4. [Data model overview](#data-model-overview)
5. [Project components](#project-components)
6. [Configuration](#configuration)
7. [Installation](#installation)
8. [How to run: common workflows](#how-to-run-common-workflows)
9. [How multi-source ingestion works](#how-multi-source-ingestion-works)
10. [How legacy ingest+query works](#how-legacy-ingestquery-works)
11. [How to inspect outputs/stores](#how-to-inspect-outputsstores)
12. [Troubleshooting](#troubleshooting)
13. [Tests](#tests)
14. [Current limitations](#current-limitations)

---

## What PaperWeb does

PaperWeb helps you build a local memory layer over research papers:
- discovers papers from one or more sources,
- normalizes metadata to a common schema,
- deduplicates overlapping papers,
- tracks freshness/version changes over time,
- parses text/tables from PDFs,
- extracts structured claims/results,
- stores evidence in SQLite + JSON stores,
- answers grounded queries from retrieved evidence.

---

## System architecture

PaperWeb has two compatible ingest entrypoints:

1. **Multi-source ingestion foundation** (for latest-paper discovery and canonical metadata management).
2. **Legacy ingest pipeline** (for parsing/extraction/vector/graph/result memory generation).

The query side uses router → retrieval → fusion → grounded generation.

---

## Pipeline tree (high-level)

```text
PaperWeb
├── Ingestion (foundation path)
│   ├── Multi-source connectors
│   │   ├── arXiv connector
│   │   ├── Semantic Scholar connector
│   │   └── OpenAlex connector
│   ├── Normalize to PaperMetadata
│   ├── Identity resolution + deduplication
│   ├── Metadata enrichment/merge
│   ├── Freshness + version tracking
│   └── Persist canonical papers (SQLite payload)
│
├── Ingestion (legacy path)
│   ├── Conference crawler adapters
│   ├── PDF/text parsing into chunks
│   ├── Extraction (facts/claims/interpretations/results)
│   ├── Validation + entity normalization
│   ├── Storage
│   │   ├── Structured DB (papers/chunks/extracted)
│   │   ├── Semantic graph (nodes/edges)
│   │   ├── Vector-like store (token overlap)
│   │   └── Result store (numeric records)
│   ├── Topic consolidation
│   └── Obsidian note generation + reindex
│
└── Query pipeline
    ├── Query router
    ├── Multi-store retrieval
    ├── Fusion/reranking
    └── Grounded generation
```

---

## Data model overview

`PaperMetadata` is the canonical normalized metadata schema used across connectors and persistence.

Important fields include:
- identity: `paper_id`, `doi`, `arxiv_id`, `openreview_id`, `semantic_scholar_id`, `openalex_id`
- bibliographic: `title`, `abstract`, `authors`, `published_date`, `updated_date`, `venue`, `year`
- links: `source`, `source_url`, `pdf_url`, `pdf_path`, `code_url`
- impact/context: `citation_count`, `reference_count`, `influential_citation_count`, `fields_of_study`, `topics`
- provenance/history: `raw_source_payload`, `source_seen_history`, `field_provenance`
- freshness/versioning: `first_seen_at`, `last_seen_at`, `version`, `metadata_hash`, `pdf_hash`, `is_new`, `is_updated`

---

## Project components

### Connectors and crawlers
- `app/crawlers/sources.py`: common connector interface + Arxiv/OpenAlex/SemanticScholar connectors.
- `app/crawlers/openreview_real.py`: arXiv-backed real crawler for legacy ingest source `openreview`.
- `app/crawlers/mock.py`: fixture-based crawlers for local deterministic runs.

### Ingestion merge/freshness
- `app/crawlers/paper_merge.py`:
  - `PaperIdentityResolver`
  - `PaperDeduplicator`
  - `MetadataEnricher`
  - `FreshnessTracker`

### Legacy parse/extract
- `app/parsing/pdf_parser.py`: PDF chunk/table extraction (plus `.txt` fixture compatibility).
- `app/extraction/extractor.py`: structured extraction handling.
- `app/validation/write_gate.py`: evidence and write validation.

### Storage
- `app/storage/structured_db.py`: SQLite `papers/chunks/extracted`.
- `app/storage/graph_store.py`: SQLite `graph_nodes/graph_edges`.
- `app/storage/vector_store.py`: local vector-like JSON store.
- `app/storage/result_store.py`: numeric result JSON store.

### Query
- `app/query_router/router.py`, `app/retrieval/*`, `app/generation/generator.py`, `app/query.py`.

---

## Configuration

PaperWeb uses `config/paperweb.toml` (or `PAPERWEB_CONFIG` override) for default behavior.

Example:

```toml
[llm]
openai_api_key = ""

[llm.router]
provider = "mock"
model = "gpt-4.1-mini"

[llm.extractor]
provider = "mock"
model = "gpt-4.1-mini"

[llm.generator]
provider = "mock"
model = "gpt-4.1-mini"

[ingestion]
source = "mock"
limit = 5
research_field = "nlp"
paper_type = "recent"
search_query = ""
```

Environment variables commonly used:
- `PAPERWEB_CONFIG` (optional path override)
- `OPENAI_API_KEY` (if using `openai` provider)

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

---

## How to run: common workflows

### A) Multi-source latest-paper discovery (foundation ingest)

Use this when your goal is broad discovery + canonical metadata + dedup + freshness tracking.

```bash
python -m app.ingest \
  --query "agentic information retrieval evaluation" \
  --sources arxiv,semantic_scholar,openalex \
  --limit 50
```

This prints summary counters for fetched/new/updated/duplicates merged/failed sources.

### B) Legacy ingest pipeline (parse + extraction memory generation)

```bash
python -m app.ingest --source mock --limit 5
```

Or real crawler mode:

```bash
python -m app.ingest --source openreview --limit 10 --field nlp --paper-type recent
```

### C) Consolidate topics + reindex notes

```bash
python -m app.consolidate
python -m app.reindex_obsidian
```

### D) Grounded querying

```bash
python -m app.query "Compare recent adaptive compression papers on KILT"
```

---

## How multi-source ingestion works

When `--query` is provided, ingest runs connector mode:

1. Call selected connectors (`--sources`) and normalize to `PaperMetadata`.
2. Deduplicate by identity priority:
   - DOI
   - arXiv ID
   - OpenReview ID
   - Semantic Scholar ID
   - OpenAlex ID
   - normalized title fallback
3. Merge richer metadata across duplicates.
4. Apply freshness tracking:
   - `first_seen_at`/`last_seen_at`
   - version increment if metadata/pdf hash changed
   - set `is_new` and `is_updated`
5. Persist canonical paper payloads into SQLite `papers` table.

---

## How legacy ingest+query works

Legacy ingest path builds retrieval memory:
- paper crawl,
- parse into chunks,
- extract structured records,
- validate,
- write to graph/vector/result stores,
- consolidate topic notes,
- reindex notes.

Query path:
- route query,
- retrieve from vector/graph/result,
- fuse evidence,
- generate grounded output.

---

## How to inspect outputs/stores

Primary files:
- `data/paperweb.db` (SQLite tables for metadata + graph)
- `data/vector_store.json`
- `data/result_store.json`
- `data/paper_index.json` (freshness/version index)

Quick checks:

```bash
sqlite3 data/paperweb.db ".tables"
sqlite3 data/paperweb.db "SELECT COUNT(*) FROM papers;"
sqlite3 data/paperweb.db "SELECT COUNT(*) FROM graph_nodes;"
sqlite3 data/paperweb.db "SELECT COUNT(*) FROM graph_edges;"
```

---

## Troubleshooting

- **No API key errors**: set `OPENAI_API_KEY` or keep providers as `mock` in config.
- **External source failure**: connector mode logs warnings and continues other sources.
- **Few/empty results**: try broader `--query` or fewer source filters.
- **Proxy/network issues**: run with `--source mock` for offline test flow.

---

## Tests

```bash
pytest
```

Notable coverage includes connector normalization, deduplication, metadata merging, and freshness tracking behavior.

---

## Current limitations

- PDF section detection is heuristic (`pdfplumber` based).
- Anthropic provider remains a stub.
- Retrieval/reranking remains MVP-style (future passes can expand ranking quality).

## Optional field/lab intelligence (abstract-only topic taxonomy)

PaperWeb includes an optional intelligence workflow that reads existing outputs (especially `data/paperweb.db`) and builds a field/lab strategy report.

- It is fully opt-in and does not change default ingest/query/consolidate/reindex behavior.
- Topic buckets are inferred from **abstracts only**.
- Papers are assigned to a fixed K-topic taxonomy (plus `OTHER` for low-fit papers).

Example:

```bash
python scripts/analyze_field_intelligence.py \
  --db data/paperweb.db \
  --field "information retrieval" \
  --lab-name "University of Queensland" \
  --out reports/field_intelligence.md \
  --top-k 15 \
  --recent-years 3 \
  --historical-years 5 \
  --topic-k 8 \
  --taxonomy-out reports/intelligence_taxonomy.json \
  --assignments-out reports/topic_assignments.json \
  --min-fit-score 0.45
```

Outputs:
- `reports/field_intelligence.md` (report)
- `reports/intelligence_taxonomy.json` (generated/reused taxonomy)
- `reports/topic_assignments.json` (paper assignments)

Limitations:
- Abstract-only inference may miss full-text nuance.
- Sparse abstracts reduce topic-assignment fidelity.

## Five-role LLM lineup and cost controls

PaperWeb supports five logical LLM roles (each configurable independently):
- `router`
- `extractor`
- `generator`
- `topic_extractor`
- `semantic_summarizer`

Recommended cost-aware defaults use mini models for bulk tasks and a stronger model for final generation.

```toml
[llm.router]
provider = "openai"
model = "gpt-5.4-mini"

[llm.extractor]
provider = "openai"
model = "gpt-5.4-mini"

[llm.generator]
provider = "openai"
model = "gpt-5.4"

[llm.topic_extractor]
provider = "openai"
model = "gpt-5.4-mini"

[llm.semantic_summarizer]
provider = "openai"
model = "gpt-5.4-mini"

[llm.cost_limits]
enabled = true
max_estimated_run_cost_usd = 5.00
warn_after_estimated_cost_usd = 1.00
```

Token/cost tracking is recorded per role in `app/llm/usage_tracker.py`, including call counts, token totals, and estimated costs.
For intelligence batch runs, use `--dry-run-cost`, `--max-papers`, `--force`, and `--ignore-cost-limit`.

## Centralized LLM config, usage tracking, and dashboard

All 5 LLM roles are centrally configured in `config/paperweb.toml` and accessed via `get_llm_role_config(role)`.
This includes model, token limits, temperature, enabled flag, and cost limits.

Usage/cost tracking is persisted to `data/llm_usage.sqlite` per call with role/model/provider/run/module metadata.

Dry-run and safeguards:
- `--dry-run-cost` estimates cost without API calls.
- `--max-papers` limits batch size.
- `--force` / `--ignore-cost-limit` override cost-limit stop behavior.

Generate dashboard:

```bash
python scripts/llm_usage_dashboard.py --usage-db data/llm_usage.sqlite --out reports/llm_usage_dashboard.html
```

## Streamlit UI

Launch the UI:

```bash
streamlit run streamlit_app.py
```

### Create/switch DB collections

- Use the sidebar to select an existing SQLite DB under `data/dbs/*.db`.
- Use **Create and switch** to make a new collection DB (for example `agentic_ir.db`, `compression.db`).
- The active DB is always shown at the top of the sidebar and all tables/pipeline writes are scoped to that DB.

### Recommended workflow for separate collections

1. Create one DB per project/topic (e.g., `data/dbs/agentic_ir.db`).
2. Run ingestion pipeline from the UI with source/query/limit controls.
3. Run query only after pipeline stages complete for that same DB.
4. Switch DB only when you want to change collection context; papers/chunks/extracted/graph/semantic data are separated by DB.

### Monitor models, progress, and usage

- The top dashboard shows model lineup for router/extractor/generator/topic_extractor/semantic_summarizer.
- Pipeline panel shows progress + event logs for ingestion and extraction stages.
- Usage panel reads the usage tracker SQLite table and shows real API call counts/tokens/cost by role.

### Browse, query, and export

- Query panel displays answer text, citations, router plan, and retrieved evidence rows.
- Dataset explorer lets you browse papers, chunks, extracted payloads, graph nodes/edges, and semantic payloads.
- Each table tab supports search and export to JSON/CSV.

## Optional Agents SDK Layer

PaperWeb remains a **research-memory pipeline** (ingestion, parsing, extraction, storage, retrieval, fusion, grounded generation). The Agents SDK layer is optional and used only for high-level multi-step workflows.

### Used for
- Complex research Q&A over memory
- Research-direction discovery
- Literature review/report generation
- Field/lab intelligence exploration
- Multi-paper evidence comparison

### Not used for
- Ingestion/source connectors
- PDF parsing/chunking
- Normalization/dedup/freshness/versioning
- Deterministic DB writes
- Single-paper simple extraction/topic labeling
- Basic grounded Q&A unless router selects multi-step orchestration

### Routing behavior
`QueryRouter.select_execution_route()` chooses:
- `pipeline` for simple grounded Q&A
- `agents` for planning/comparison/report-style multi-step queries
- if `[agents].enabled=false` or agent errors, fallback to normal pipeline

### Tool mapping
Agent tools wrap existing stores/functions (SQL metadata, vector store, graph neighbors, semantic facts, chunks/facts, topic stats, field intelligence, grounded report).

### Enablement
Configure in `config/paperweb.toml` under `[agents]` and sub-sections.

### CLI
- `python -m app.agents.cli ask "..."`
- `python -m app.agents.cli report --topic "..."`
- `python -m app.agents.cli trace --last`

### Tracing and usage
- Agent traces are logged in `data/agent_traces.jsonl`
- Token/cost usage is recorded in existing `data/llm_usage.sqlite`
