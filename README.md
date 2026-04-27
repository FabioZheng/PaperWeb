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

## LLM roles and providers
Three explicit roles are implemented:
- Router LLM (`ROUTER_PROVIDER`, `ROUTER_MODEL`)
- Extraction LLM (`EXTRACTOR_PROVIDER`, `EXTRACTOR_MODEL`)
- Generation LLM (`GENERATOR_PROVIDER`, `GENERATOR_MODEL`)

Supported provider adapters:
- `mock` (default, deterministic, no API key)
- `openai` (fully implemented)
- `anthropic` (integration point stub)

> For OpenAI set `OPENAI_API_KEY` and provider/model environment variables.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run locally

### Ingest papers (real API-backed)
```bash
python -m app.ingest --source openreview --limit 5
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

## LLM config example
```bash
export ROUTER_PROVIDER=openai
export ROUTER_MODEL=gpt-4.1-mini
export EXTRACTOR_PROVIDER=openai
export EXTRACTOR_MODEL=gpt-4.1-mini
export GENERATOR_PROVIDER=openai
export GENERATOR_MODEL=gpt-4.1-mini
export OPENAI_API_KEY=your_key_here
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
