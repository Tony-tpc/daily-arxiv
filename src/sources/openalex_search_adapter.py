"""OpenAlex search adapter: discover high-impact papers by topic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.utils import get_date_string, save_json

from .base import BaseSourceAdapter


class OpenAlexSearchAdapter(BaseSourceAdapter):
    """Discover papers via OpenAlex search, sorted by citation impact."""

    source_name = "openalex_search"
    base_url = "https://api.openalex.org"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        sources = config.get("sources", {}) if isinstance(config, dict) else {}
        self._source_config = sources.get("openalex_search", {}).copy() if isinstance(sources, dict) else {}
        if not isinstance(self._source_config, dict):
            self._source_config = {}
        self._source_config.setdefault("enabled", True)

        oa = sources.get("openalex", {}) if isinstance(sources, dict) else {}
        self.api_key = oa.get("api_key", "") if isinstance(oa, dict) else ""
        self.timeout = float(self._source_config.get("request_timeout_seconds", 20))
        self.per_page = int(self._source_config.get("per_page", 25))
        self.select_fields = [
            "id", "doi", "title", "display_name", "publication_year",
            "cited_by_count", "primary_topic", "topics", "concepts",
            "authorships", "referenced_works_count", "ids", "updated_date",
        ]
        self.client = httpx.Client(timeout=self.timeout)

    @property
    def source_config(self) -> Dict[str, Any]:
        return self._source_config

    def validate(self) -> None:
        if not self.api_key:
            self.logger.warning(
                "OpenAlex search requires api_key under sources.openalex; "
                "set OPENALEX_API_KEY in .env or sources.openalex.api_key in config.yaml"
            )

    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        days_back = int(kwargs.get("days_back", 0) or 0)
        search_terms = self._build_search_terms()
        if not search_terms:
            self.logger.warning("No search terms configured for OpenAlex search adapter")
            return []

        all_results: List[Dict[str, Any]] = []
        max_results = int(self._source_config.get("max_results", kwargs.get("max_results", 20)))

        for term in search_terms:
            params = {
                "search": term,
                "sort": "cited_by_count:desc",
                "per_page": str(self.per_page),
                "select": ",".join(self.select_fields),
            }
            if days_back > 0:
                year_from = datetime.now().year - max(1, days_back // 365)
                if year_from >= 2000:
                    params["filter"] = f"from_publication_date:{year_from}-01-01"

            self.logger.info(
                self.fetcher_text(
                    f"OpenAlex 搜索: {term[:60]}...",
                    f"OpenAlex search: {term[:60]}...",
                )
            )

            works = self._search_works(params)
            for work in works[:max_results]:
                record = self._work_to_record(work)
                if not any(r.get("id") == record["id"] for r in all_results):
                    all_results.append(record)

            if len(all_results) >= max_results:
                break

        all_results = all_results[:max_results]
        self.save_raw_snapshot(all_results)
        self.logger.info(
            self.fetcher_text(
                f"\u2705 OpenAlex \u641c\u7d22\u5b8c\u6210: {len(all_results)} \u7bc7\u8bba\u6587",
                f"\u2705 OpenAlex search complete: {len(all_results)} papers",
            )
        )
        return all_results

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return records

    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        import os
        from pathlib import Path
        date_str = get_date_string()
        data_dir = os.path.join("data", "papers")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(data_dir, f"openalex_search_{date_str}.json")
        latest_path = os.path.join(data_dir, "latest_openalex.json")
        payload = {"date": date_str, "count": len(records), "papers": records}
        save_json(payload, path)
        save_json(payload, latest_path)

    def print_summary(self, records: List[Dict[str, Any]]) -> None:
        for i, paper in enumerate(records, 1):
            self.logger.info(
                self.fetcher_text(
                    f"[{i}] {paper.get('title','')[:70]} | \u5f15\u7528: {paper.get('citation_count',0)}",
                    f"[{i}] {paper.get('title','')[:70]} | cites: {paper.get('citation_count',0)}",
                )
            )

    def fetcher_text(self, zh: str, en: str) -> str:
        lang = self.config.get("app", {}).get("language", "zh") if isinstance(self.config, dict) else "zh"
        return en if str(lang).startswith("en") else zh

    def _build_search_terms(self) -> List[str]:
        terms = self._source_config.get("search_terms", [])
        if terms:
            return [str(t).strip() for t in terms if str(t).strip()]

        keyword_groups = self._source_config.get("keyword_groups", [])
        if not keyword_groups:
            tracking = self.config.get("tracking_topics", []) if isinstance(self.config, dict) else []
            if tracking:
                return [" ".join(str(t).strip() for t in tracking if str(t).strip())]
            return []

        queries = []
        for group in keyword_groups:
            if isinstance(group, dict):
                group_terms = group.get("terms", [])
            else:
                group_terms = group
            joined = " ".join(str(t).strip() for t in group_terms if str(t).strip())
            if joined:
                queries.append(joined)
        return queries

    def _search_works(self, params: Dict[str, str]) -> List[Dict[str, Any]]:
        headers = {}
        if self.api_key:
            headers["api-key"] = self.api_key
        response = self.client.get(f"{self.base_url}/works", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])

    def _work_to_record(self, work: Dict[str, Any]) -> Dict[str, Any]:
        ids = work.get("ids", {}) or {}
        arxiv_id = ids.get("arxiv")
        entry_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

        authors = []
        for a in work.get("authorships", []):
            name = a.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)

        institutions = []
        for a in work.get("authorships", [])[:100]:
            for i in a.get("institutions", []):
                name = i.get("display_name", "")
                if name and name not in institutions:
                    institutions.append(name)

        primary_topic = work.get("primary_topic") or {}
        topics = [t.get("display_name", "") for t in work.get("topics", []) if t.get("display_name")]
        concepts = [c.get("display_name", "") for c in work.get("concepts", []) if c.get("display_name")]

        doi_raw = work.get("doi", "")
        doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""
        doi_url = f"https://doi.org/{doi}" if doi else ""

        return {
            "id": arxiv_id or work.get("id", "").split("/")[-1],
            "title": work.get("display_name") or work.get("title", ""),
            "authors": authors,
            "abstract": "",
            "categories": [t for t in topics[:3]],
            "primary_category": topics[0] if topics else "",
            "published": work.get("publication_year", ""),
            "updated": work.get("updated_date", ""),
            "pdf_url": entry_url.replace("/abs/", "/pdf/") if entry_url else doi_url,
            "entry_url": entry_url or doi_url or work.get("id", ""),
            "comment": None,
            "journal_ref": None,
            "doi": doi,
            "fetched_at": datetime.now().isoformat(),
            "openalex_id": work.get("id"),
            "citation_count": work.get("cited_by_count", 0),
            "openalex_topics": topics,
            "openalex_concepts": concepts,
            "openalex_primary_topic": primary_topic.get("display_name"),
            "openalex_institutions": institutions,
            "openalex_referenced_works": [],
            "openalex_referenced_works_count": work.get("referenced_works_count", 0),
            "openalex_updated_date": work.get("updated_date"),
            "openalex_enriched_at": datetime.now().isoformat(),
            "impact_bracket": self._bracket(work.get("cited_by_count", 0)),
        }

    @staticmethod
    def _bracket(cites: int) -> str:
        if cites >= 100:
            return "hot"
        if cites >= 25:
            return "high"
        if cites >= 5:
            return "notable"
        return ""
