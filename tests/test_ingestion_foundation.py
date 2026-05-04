from app.crawlers.paper_merge import FreshnessTracker, MetadataEnricher, PaperDeduplicator
from app.crawlers.sources import ArxivConnector, OpenAlexConnector, SemanticScholarConnector
from app.models import PaperMetadata


def test_arxiv_connector_normalization(monkeypatch):
    sample = """
    <feed>
      <entry>
        <id>http://arxiv.org/abs/2501.00001v1</id>
        <updated>2025-01-02T00:00:00Z</updated>
        <published>2025-01-01T00:00:00Z</published>
        <title>Sample Title</title>
        <summary>Sample abstract</summary>
        <author><name>Alice</name></author>
        <link title=\"pdf\" href=\"https://arxiv.org/pdf/2501.00001v1.pdf\"/>
      </entry>
    </feed>
    """

    class R:
        text = sample

    monkeypatch.setattr("httpx.get", lambda *a, **k: R())
    papers = ArxivConnector().search("test", limit=1)
    assert papers[0].arxiv_id == "2501.00001v1"
    assert papers[0].source == "arxiv"


def test_openalex_connector_normalization(monkeypatch):
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "title": "OpenAlex Title",
                "doi": "https://doi.org/10.1/abc",
                "publication_date": "2024-01-01",
                "publication_year": 2024,
                "authorships": [{"author": {"display_name": "Bob"}}],
                "concepts": [{"display_name": "IR"}],
            }
        ]
    }

    class R:
        def json(self):
            return payload

    monkeypatch.setattr("httpx.get", lambda *a, **k: R())
    papers = OpenAlexConnector().search("test", limit=1)
    assert papers[0].openalex_id == "W123"
    assert papers[0].title == "OpenAlex Title"


def test_semantic_connector_normalization(monkeypatch):
    payload = {
        "data": [
            {
                "paperId": "S2-1",
                "title": "S2 Title",
                "abstract": "A",
                "authors": [{"name": "Eve"}],
                "externalIds": {"DOI": "10.2/x", "ArXiv": "2501.2"},
                "publicationDate": "2024-02-01",
            }
        ]
    }

    class R:
        def json(self):
            return payload

    monkeypatch.setattr("httpx.get", lambda *a, **k: R())
    papers = SemanticScholarConnector().search("test", limit=1)
    assert papers[0].semantic_scholar_id == "S2-1"
    assert papers[0].doi == "10.2/x"


def _paper(**kwargs):
    base = dict(paper_id="p", title="Same Title", source="s", source_url="u")
    base.update(kwargs)
    return PaperMetadata(**base)


def test_dedup_by_doi():
    a = _paper(paper_id="a", source="arxiv", doi="10.1/a", authors=["A"])
    b = _paper(paper_id="b", source="openalex", doi="10.1/a", abstract="longer abstract")
    result = PaperDeduplicator().deduplicate([a, b])
    assert len(result.papers) == 1
    assert result.duplicates_merged == 1


def test_dedup_by_arxiv_and_semantic_ids():
    a = _paper(paper_id="a", source="arxiv", arxiv_id="1234.1")
    b = _paper(paper_id="b", source="semantic_scholar", arxiv_id="1234.1", semantic_scholar_id="S2")
    result = PaperDeduplicator().deduplicate([a, b])
    assert len(result.papers) == 1


def test_dedup_by_title_fallback():
    a = _paper(paper_id="a", source="x", title="Agentic Retrieval: A Survey")
    b = _paper(paper_id="b", source="y", title="agentic retrieval a survey")
    result = PaperDeduplicator().deduplicate([a, b])
    assert len(result.papers) == 1


def test_metadata_enrichment_prefers_non_empty():
    base = _paper(paper_id="a", source="x", abstract=None, authors=["A"])
    other = _paper(paper_id="b", source="y", abstract="Useful abstract", authors=["A", "B"])
    merged = MetadataEnricher().merge(base, other)
    assert merged.abstract == "Useful abstract"
    assert len(merged.authors) == 2


def test_freshness_tracking_new_and_updated(tmp_path):
    tracker = FreshnessTracker(path=str(tmp_path / "idx.json"))
    p1 = _paper(paper_id="a", source="x", doi="10.9/z", abstract="v1")
    papers, new_count, updated_count = tracker.apply([p1])
    assert papers[0].is_new is True
    assert new_count == 1 and updated_count == 0

    p2 = _paper(paper_id="a2", source="x", doi="10.9/z", abstract="v2")
    papers2, new_count2, updated_count2 = tracker.apply([p2])
    assert papers2[0].is_new is False
    assert papers2[0].is_updated is True
    assert new_count2 == 0 and updated_count2 == 1
