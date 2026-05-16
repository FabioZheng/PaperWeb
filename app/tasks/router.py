from __future__ import annotations


def detect_task(query: str) -> str:
    q = query.lower().strip()
    if q.startswith("what is") or "acronym" in q:
        return "define_concept"
    if "which paper" in q or "proposed" in q:
        return "paper_lookup"
    if "compare" in q:
        return "compare_papers"
    if "results" in q:
        return "extract_results"
    if "research directions" in q or "main directions" in q:
        return "field_mapping"
    if "summarize" in q:
        return "summarize_paper"
    return "qa_selected_papers"
