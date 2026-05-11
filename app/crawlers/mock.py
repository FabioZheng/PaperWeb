"""Mock crawler backends for offline MVP runs."""

from __future__ import annotations

import json
from pathlib import Path

from app.crawlers.base import ConferenceCrawler
from app.models import PaperMetadata


class MockFileCrawler(ConferenceCrawler):
    def __init__(self, fixture_path: str = "fixtures/papers/mock_papers.json"):
        self.fixture_path = Path(fixture_path)

    def fetch_recent(self, limit: int) -> list[PaperMetadata]:
        data = json.loads(self.fixture_path.read_text(encoding="utf-8", errors="replace"))
        return [PaperMetadata.model_validate(row) for row in data[:limit]]


class OpenReviewStyleCrawler(MockFileCrawler):
    """OpenReview-style adapter using local sample data for MVP."""


class ACLCVFStyleCrawler(MockFileCrawler):
    """ACL/CVF-style adapter using local sample data for MVP."""
