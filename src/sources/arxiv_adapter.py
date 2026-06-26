"""Thin adapter that wraps the existing arXiv fetcher implementation."""

from __future__ import annotations

from typing import Any, Dict, List

from src.crawler.arxiv_fetcher import ArxivFetcher
from src.sources.openalex_adapter import OpenAlexAdapter
from src.utils import get_data_path, get_date_string, save_json

from pathlib import Path

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

    def save_enriched_snapshot(self, records: List[Dict[str, Any]]) -> None:
        data_path = get_data_path(self.config, 'papers')
        Path(data_path).mkdir(parents=True, exist_ok=True)
        date_str = get_date_string()
        filepath = f"{data_path}/papers_enriched_{date_str}.json"
        latest_filepath = f"{data_path}/latest_enriched.json"
        save_json(records, filepath)
        save_json({
            'date': date_str,
            'count': len(records),
            'papers': records,
        }, latest_filepath)
        self.logger.info(self.fetcher.text(f"💾 enriched 论文数据已保存到: {filepath}", f"💾 Enriched paper data saved to: {filepath}"))
        self.logger.info(self.fetcher.text(f"💾 enriched 最新数据已保存到: {latest_filepath}", f"💾 Enriched latest data saved to: {latest_filepath}"))

    def print_summary(self, records: List[Dict[str, Any]]) -> None:
        self.fetcher.print_paper_summary(records)
