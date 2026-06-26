"""OpenAlex enrichment adapter for arXiv-fetched paper records."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.utils import load_json, save_json


class OpenAlexAdapter:
    """Lightweight OpenAlex enrichment client with local JSON caching."""

    base_url = "https://api.openalex.org"
    MISS = {"miss": True}

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        sources = config.get("sources", {}) if isinstance(config, dict) else {}
        self.source_config = sources.get("openalex", {}) if isinstance(sources, dict) else {}
        self.logger = logging.getLogger("daily_arxiv.sources.openalex")
        self.timeout = float(self.source_config.get("request_timeout_seconds", 20))
        self.max_title_search_results = int(self.source_config.get("max_title_search_results", 5))
        self.select_fields = self.source_config.get(
            "select_fields",
            [
                "id",
                "doi",
                "title",
                "display_name",
                "publication_year",
                "cited_by_count",
                "primary_topic",
                "topics",
                "authorships",
                "referenced_works",
                "referenced_works_count",
                "ids",
                "updated_date",
            ],
        )
        self.cache_path = self.source_config.get("cache_path", "data/cache/openalex_works.json")
        self.cache = load_json(self.cache_path) or {"by_key": {}}
        self.client = httpx.Client(timeout=self.timeout)

    def enrich_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich paper records with OpenAlex metadata."""
        if not self.source_config.get("enabled", False):
            return list(records)

        if not self.source_config.get("api_key"):
            self.logger.warning(
                "OpenAlex enrichment is enabled but no api_key is configured - "
                "lookups may fail or be heavily rate-limited. "
                "Set OPENALEX_API_KEY in your .env file."
            )

        enriched = []
        hits = missed = 0
        for record in records:
            before_keys = set(record.keys())
            result = self.enrich_record(record)
            if len(set(result.keys()) - before_keys) <= 1:
                missed += 1
            else:
                hits += 1
            enriched.append(result)

        self.logger.info(f"OpenAlex enrichment: {hits} enriched, {missed} unchanged")
        self._persist_cache()
        return enriched

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single paper record."""
        work = self._resolve_work(record)
        if not work:
            return record

        enriched = dict(record)
        enriched["openalex_id"] = work.get("id")
        enriched["citation_count"] = work.get("cited_by_count", 0)
        enriched["openalex_topics"] = [topic.get("display_name") for topic in work.get("topics", []) if topic.get("display_name")]
        enriched["openalex_concepts"] = [concept.get("display_name") for concept in work.get("concepts", []) if concept.get("display_name")]
        primary_topic = work.get("primary_topic") or {}
        enriched["openalex_primary_topic"] = primary_topic.get("display_name")
        enriched["openalex_institutions"] = self._extract_institutions(work)
        enriched["openalex_referenced_works"] = work.get("referenced_works", [])
        enriched["openalex_referenced_works_count"] = work.get("referenced_works_count", 0)
        enriched["openalex_updated_date"] = work.get("updated_date")
        enriched["openalex_enriched_at"] = datetime.now().isoformat()
        if enriched.get("doi"):
            enriched["doi"] = self._normalize_doi(enriched.get("doi"))
        elif work.get("doi"):
            enriched["doi"] = self._normalize_doi(work.get("doi"))
        return enriched

    def _resolve_work(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doi = self._normalize_doi(record.get("doi"))
        if doi:
            work = self._lookup_by_doi(doi)
            if work:
                return work

        arxiv_id = str(record.get("id") or "").strip()
        if arxiv_id:
            work = self._search_by_arxiv_id(arxiv_id)
            if work:
                return work

        title = str(record.get("title") or "").strip()
        if title:
            return self._search_by_title(title)
        return None

    def _lookup_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        cache_key = f"doi:{doi.lower()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        path = f"/works/doi:{doi}"
        work = self._request_json(path, {"select": ",".join(self.select_fields)}, treat_not_found_as_miss=True)
        self._set_cache(cache_key, work)
        return work

    def _search_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f"arxiv:{arxiv_id.lower()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        search_term = arxiv_id
        works = self._list_works(
            {
                "search": search_term,
                "per_page": str(self.max_title_search_results),
                "select": ",".join(self.select_fields),
            }
        )
        matched = next((work for work in works if self._matches_arxiv_id(work, arxiv_id)), None)
        self._set_cache(cache_key, matched)
        return matched

    def _search_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        normalized_title = self._normalize_title(title)
        cache_key = f"title:{hashlib.sha256(normalized_title.encode('utf-8')).hexdigest()}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        works = self._list_works(
            {
                "search": title,
                "per_page": str(self.max_title_search_results),
                "select": ",".join(self.select_fields),
            }
        )
        matched = next(
            (
                work
                for work in works
                if self._normalize_title(work.get("display_name") or work.get("title") or "") == normalized_title
            ),
            None,
        )
        self._set_cache(cache_key, matched)
        return matched

    def _list_works(self, params: Dict[str, str]) -> List[Dict[str, Any]]:
        payload = self._request_json("/works", params)
        return payload.get("results", []) if isinstance(payload, dict) else []

    def _request_json(
        self,
        path: str,
        params: Dict[str, str],
        *,
        treat_not_found_as_miss: bool = False,
    ) -> Optional[Dict[str, Any]]:
        headers = {}
        api_key = self.source_config.get("api_key", "")
        if api_key:
            headers["api-key"] = api_key

        response = self.client.get(f"{self.base_url}{path}", params=params, headers=headers)
        if response.status_code == 404 and treat_not_found_as_miss:
            return None
        response.raise_for_status()
        return response.json()

    def _extract_institutions(self, work: Dict[str, Any]) -> List[str]:
        institutions: List[str] = []
        for authorship in work.get("authorships", [])[:100]:
            for institution in authorship.get("institutions", []):
                display_name = institution.get("display_name")
                if display_name and display_name not in institutions:
                    institutions.append(display_name)
        return institutions

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        by_key = self.cache.get("by_key", {})
        if key not in by_key:
            return None
        cached = by_key[key]
        if cached == self.MISS:
            return self.MISS
        return cached

    def _set_cache(self, key: str, work: Optional[Dict[str, Any]]) -> None:
        self.cache.setdefault("by_key", {})[key] = work if work is not None else self.MISS

    def _persist_cache(self) -> None:
        save_json(self.cache, self.cache_path)

    @staticmethod
    def _normalize_doi(doi: Any) -> str:
        value = str(doi or "").strip()
        if not value:
            return ""
        prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
        lowered = value.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return value[len(prefix):]
        return value

    @staticmethod
    def _normalize_title(title: str) -> str:
        lowered = title.lower().strip()
        lowered = re.sub(r"\s+", " ", lowered)
        lowered = re.sub(r"[^a-z0-9\s]", "", lowered)
        return lowered.strip()

    def _matches_arxiv_id(self, work: Dict[str, Any], arxiv_id: str) -> bool:
        normalized = arxiv_id.lower()
        ids = work.get("ids", {}) or {}
        for value in ids.values():
            value_str = str(value or "").lower()
            if normalized == value_str or normalized in value_str:
                return True
        return False
