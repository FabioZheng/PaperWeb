"""Crawler interfaces for conference sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import PaperMetadata


class ConferenceCrawler(ABC):
    @abstractmethod
    def fetch_recent(self, limit: int) -> list[PaperMetadata]:
        """Return recently accepted paper metadata records."""
