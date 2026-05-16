from __future__ import annotations

from app.models import PaperMetadata
from app.paper_cards.extractor import extract_acronyms, extract_key_terms
from app.paper_cards.schema import PaperCard


def build_paper_card(meta: PaperMetadata, full_text_path: str | None = None) -> PaperCard:
    combined = " ".join([meta.title or "", meta.abstract or ""])
    return PaperCard(
        paper_id=meta.paper_id,
        title=meta.title,
        authors=meta.authors,
        year=meta.year,
        venue=meta.venue,
        source=meta.source,
        abstract=meta.abstract,
        full_text_path=full_text_path or meta.pdf_path or None,
        field=(meta.fields_of_study[0] if meta.fields_of_study else None),
        key_terms=extract_key_terms(combined),
        acronyms=extract_acronyms(combined),
    )
