from app.models import PaperMetadata
from app.paper_cards.builder import build_paper_card
from app.paper_cards.extractor import extract_acronyms
from app.tasks.router import detect_task
from app.tasks.define_concept import DefineConceptTask


def test_paper_card_creation_from_metadata_and_abstract():
    meta = PaperMetadata(paper_id="p1", title="Conformal Path Reasoning", abstract="CPR is a KGQA framework", authors=["A"], year=2024, source="mock")
    card = build_paper_card(meta)
    assert card.paper_id == "p1"
    assert "CPR" in card.acronyms


def test_acronym_extraction():
    assert extract_acronyms("WHAT IS CPR in KGQA") == ["CPR", "IS", "KGQA", "WHAT"]


def test_what_is_cpr_routes_to_define_concept_task():
    assert detect_task("what is CPR") == "define_concept"


def test_definition_task_uses_acronym_title_abstract_index():
    meta = PaperMetadata(paper_id="p1", title="Conformal Path Reasoning", abstract="CPR improves KGQA", authors=["A"], year=2024, source="mock")
    card = build_paper_card(meta)
    out = DefineConceptTask().run("what is CPR", {"paper_cards": [card]})
    assert out.selected_source == "acronym_keyterm_index"
    assert out.evidence_used
