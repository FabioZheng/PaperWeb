from __future__ import annotations

from app.paper_cards.schema import PaperCard


def validate_paper_card(card: PaperCard) -> PaperCard:
    if not card.paper_id.strip():
        raise ValueError("paper_id is required")
    if not card.title.strip():
        raise ValueError("title is required")
    return card
