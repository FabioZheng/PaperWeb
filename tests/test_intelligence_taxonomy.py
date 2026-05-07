from app.intelligence.report import build_field_intelligence_report
from app.intelligence.schema import IntelligencePaper
from app.intelligence.taxonomy import build_topic_taxonomy
from app.intelligence.topic_assignment import assign_papers_to_taxonomy
from app.intelligence.topic_stats import compute_topic_direction_stats
from app.intelligence.institution_ranking import rank_institutions_by_direction
from app.intelligence.lab_coverage import compute_lab_coverage


def _papers():
    return [
        IntelligencePaper("p1", "t1", abstract="retrieval ranking dense query expansion", year=2026, institutions=["UQ"], citation_count=10),
        IntelligencePaper("p2", "t2", abstract="retrieval indexing sparse ranking", year=2025, institutions=["UQ"], citation_count=8),
        IntelligencePaper("p3", "t3", abstract="vision segmentation transformer", year=2021, institutions=["LabX"], citation_count=20),
    ]


def test_taxonomy_and_assignment_with_other():
    papers = _papers()
    taxonomy = build_topic_taxonomy(papers, k=2, field="information retrieval")
    assert len(taxonomy) == 2

    assignments = assign_papers_to_taxonomy(papers, taxonomy, min_fit_score=0.9)
    assert any(a.primary_topic_id == "OTHER" for a in assignments)


def test_report_generation():
    papers = _papers()
    taxonomy = build_topic_taxonomy(papers, k=2, field="information retrieval")
    assignments = assign_papers_to_taxonomy(papers, taxonomy, min_fit_score=0.2)
    stats = compute_topic_direction_stats(papers, taxonomy, assignments, current_year=2026, min_topic_papers=1)
    ranks = rank_institutions_by_direction(papers, assignments, current_year=2026)
    coverage = compute_lab_coverage(papers, assignments, stats, "UQ", current_year=2026)
    out = build_field_intelligence_report("information retrieval", "UQ", taxonomy, assignments, stats, ranks, coverage)
    assert "abstracts only" in out.lower()
    assert "Generated topic taxonomy" in out
