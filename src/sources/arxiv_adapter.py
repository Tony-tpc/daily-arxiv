"""Thin adapter that wraps the existing arXiv fetcher implementation."""

from __future__ import annotations

from typing import Any, Dict, List

from src.crawler.arxiv_fetcher import ArxivFetcher
from src.sources.openalex_adapter import OpenAlexAdapter

from .base import BaseSourceAdapter


class ArxivSourceAdapter(BaseSourceAdapter):
    """Adapter wrapper around the legacy ArxivFetcher."""

    source_name = "arxiv"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fetcher = ArxivFetcher(config)
        self.openalex_adapter = OpenAlexAdapter(config)

    @property
    def source_config(self) -> Dict[str, Any]:
        sources = self.config.get("sources", {}) if isinstance(self.config, dict) else {}
        if isinstance(sources, dict) and isinstance(sources.get("arxiv"), dict):
            return sources.get("arxiv", {})
        return self.config.get("arxiv", {})

    def validate(self) -> None:
        categories = self.source_config.get("categories", self.fetcher.categories)
        if not categories:
            raise ValueError("Arxiv source requires at least one category")

    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        days_back = kwargs.get("days_back", self.source_config.get("days_back", 1))
        return self.fetcher.fetch_papers(days_back=days_back)

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.openalex_adapter.enrich_records(records)

    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        self.fetcher._save_papers(records)

    def print_summary(self, records: List[Dict[str, Any]]) -> None:
        self.fetcher.print_paper_summary(records)
