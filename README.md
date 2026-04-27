# PaperWeb MVP: Research Memory Pipeline

This repository implements a production-oriented MVP for discovering accepted papers, distilling memory, storing across multiple backends, and answering grounded queries.

## Architecture

### Ingestion pipeline
1. `crawlers/` discover recent papers (real arXiv-backed crawler + mock adapters).
2. `parsing/` parses PDF/text into typed chunks with provenance.
3. `extraction/` distills facts, claims, interpretations, and numeric results.
4. `validation/` write gate validates evidence references, deduplicates claims, normalizes entities.
5. `storage/` writes memory to:
   - vector store (`data/vector_store.json`)
   - semantic graph (`graph_nodes`/`graph_edges` in `data/paperweb.db`)
   - structured DB (`papers`, `chunks`, `extracted`)
   - result store (`data/result_store.json`)
6. `consolidation/` groups papers into topic memories.
7. `obsidian/` generates per-paper and per-topic markdown notes, then reindexes curated notes into vector memory.

### Query pipeline
1. `query_router/` rule-first planner + optional Router LLM.
2. `retrieval/` queries vector, graph, result, and curated obsidian memory.
3. Fusion and reranking produce one evidence pack.
4. `generation/` uses only the evidence pack to produce grounded output.

## LLM roles and providers (config file driven)
Three explicit roles are implemented:
- Router LLM
- Extraction LLM
- Generation LLM

Provider + model are configured in `config/paperweb.toml` under:
- `[llm.router]`
- `[llm.extractor]`
- `[llm.generator]`

Supported provider adapters:
- `mock` (default, deterministic, no API key)
- `openai` (fully implemented)
- `anthropic` (integration point stub)

Set OpenAI key in config (`[llm].openai_api_key`) or via `OPENAI_API_KEY`.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Configure before running
Edit `config/paperweb.toml`.

Example:
```toml
[llm]
openai_api_key = "sk-..."

[llm.router]
provider = "openai"
model = "gpt-4.1-mini"

[llm.extractor]
provider = "openai"
model = "gpt-4.1-mini"

[llm.generator]
provider = "openai"
model = "gpt-4.1-mini"

[ingestion]
source = "openreview"
limit = 20
research_field = "nlp"
paper_type = "survey"
search_query = ""
```

`research_field` controls arXiv category focus (`nlp`, `cv`, `ml`, `ai`, `robotics`, `all`).
`paper_type` can be `recent`/`latest`/`all` or any keyword (e.g. `survey`, `benchmark`) which gets added to the query.

## Run locally

### Ingest papers (real API-backed, using config defaults)
```bash
python -m app.ingest
```

### Ingest papers with explicit overrides
```bash
python -m app.ingest --source openreview --limit 10 --field cv --paper-type survey
python -m app.ingest --source openreview --search-query "cat:cs.LG AND all:retrieval"
```

### Ingest papers (fixtures)
```bash
python -m app.ingest --source mock --limit 5
```

### Consolidate topics
```bash
python -m app.consolidate
```

### Re-index Obsidian notes
```bash
python -m app.reindex_obsidian
```

### Run grounded query
```bash
python -m app.query "Compare recent adaptive compression papers on KILT"
```

## Fixtures / mock mode
- Input papers: `fixtures/papers/mock_papers.json`
- Mock paper texts: `fixtures/papers/p1.txt`, `fixtures/papers/p2.txt`
- Obsidian vault: `fixtures/obsidian_vault/`

Mock mode remains available for deterministic tests.

## Tests
```bash
pytest
```

## Limitations / TODOs
- PDF parsing uses `pdfplumber`; section detection is heuristic.
- Anthropic adapter remains a stub until credentials and SDKs are enabled.
- Graph query set is intentionally minimal but includes contradiction/refinement relation support.
