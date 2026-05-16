from __future__ import annotations

import re

ACRONYM_RE = re.compile(r"\b[A-Z]{2,8}\b")
TERM_RE = re.compile(r"\b[a-zA-Z][a-zA-Z\-]{2,}\b")


def extract_acronyms(text: str | None) -> list[str]:
    if not text:
        return []
    return sorted(set(ACRONYM_RE.findall(text)))


def extract_key_terms(text: str | None, *, top_k: int = 12) -> list[str]:
    if not text:
        return []
    seen: list[str] = []
    for t in TERM_RE.findall(text.lower()):
        if t not in seen:
            seen.append(t)
        if len(seen) >= top_k:
            break
    return seen
