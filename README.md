# PaperWeb MVP: Research Memory Pipeline

This repository implements a production-oriented MVP for discovering accepted papers, distilling memory, storing across multiple backends, and answering grounded queries.

## Architecture

### Ingestion pipeline
1. `crawlers/` discover recent papers (mock OpenReview/ACL-CVF adapters).
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
- `openai` (integration point stub)
- `anthropic` (integration point stub)

> For live providers, wire API clients in `app/extraction/llm_provider.py` and use `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run locally

### Ingest papers
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

Everything runs without external credentials in mock mode.

## Tests
```bash
pytest
```

## Limitations / TODOs
- PDF parser is a text-fixture MVP with a clear interface for real PDF extractors.
- OpenAI/Anthropic adapters are intentionally stubbed until credentials and SDKs are enabled.
- Graph query set is intentionally minimal but includes contradiction/refinement relation support.
