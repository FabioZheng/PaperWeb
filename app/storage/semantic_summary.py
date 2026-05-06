from __future__ import annotations

from app.extraction.llm_provider import build_provider


def build_semantic_summary(title: str, abstract: str) -> dict:
    provider = build_provider("semantic_summarizer")
    prompt = (
        "Return JSON with keys: global_summary, main_findings, main_claims, evidence_summary, methods, datasets, limitations, keywords. "
        "Use concise output.\n"
        f"TITLE: {title}\nABSTRACT: {abstract}"
    )
    try:
        return provider.complete_json(prompt)
    except Exception:
        return {
            "global_summary": abstract[:400],
            "main_findings": [],
            "main_claims": [],
            "evidence_summary": "",
            "methods": [],
            "datasets": [],
            "limitations": [],
            "keywords": [],
        }
