from __future__ import annotations

from app.paper_cards.schema import PaperCard


def match_acronym_or_term(cards: list[PaperCard], query: str) -> list[PaperCard]:
    q = query.strip().lower()
    out: list[PaperCard] = []
    for c in cards:
        text = " ".join([c.title, c.abstract or "", " ".join(c.acronyms), " ".join(c.key_terms)]).lower()
        if q and q in text:
            out.append(c)
    return out
