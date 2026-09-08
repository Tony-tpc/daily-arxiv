"""OpenAlex search adapter: discover high-impact papers by topic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.utils import get_date_string, save_json

from .base import BaseSourceAdapter
from .paper_normalizer import extract_arxiv_id, normalize_paper_records
from .paper_quality import enrich_openalex_venue_metadata


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
            "publication_date",
            "cited_by_count", "primary_topic", "topics", "concepts", "type",
            "primary_location",
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
        max_results = int(self._source_config.get("max_results", kwargs.get("max_results", 20)))
        all_results: List[Dict[str, Any]] = []

        search_terms = self._build_search_terms()

        if search_terms == ["__concept_filter__"]:
            try:
                all_results = self._fetch_by_concepts(max_results)
            except httpx.HTTPStatusError as exc:
                if not _is_rate_limited(exc):
                    raise
                all_results = self._fetch_crossref_fallback(max_results, [])
        else:
            for index, term in enumerate(search_terms):
                if not term:
                    continue
                params = {
                    "search": term,
                    "sort": "cited_by_count:desc",
                    "per_page": str(self.per_page),
                    "select": ",".join(self.select_fields),
                }
                self.logger.info(self.fetcher_text(f"OpenAlex 搜索: {term[:60]}...", f"OpenAlex search: {term[:60]}..."))
                try:
                    works = self._search_works(params)
                except httpx.HTTPStatusError as exc:
                    if not _is_rate_limited(exc):
                        raise
                    self.logger.warning(self.fetcher_text(
                        "OpenAlex 触发限流，改用 Crossref 期刊元数据兜底。",
                        "OpenAlex rate-limited; using the Crossref journal-metadata fallback.",
                    ))
                    all_results.extend(self._fetch_crossref_fallback(
                        max_results - len(all_results), search_terms[index:]
                    ))
                    break
                for work in works:
                    record = self._work_to_record(work)
                    if self._is_survey(record):
                        continue
                    if not any(r.get("id") == record["id"] for r in all_results):
                        all_results.append(record)
                    if len(all_results) >= max_results:
                        break
                if len(all_results) >= max_results:
                    break

        all_results = _unique_records(all_results)[:max_results]
        self.save_raw_snapshot(all_results)
        self.logger.info(self.fetcher_text(f"\u2705 OpenAlex 搜索完成: {len(all_results)} 篇论文", f"\u2705 OpenAlex search complete: {len(all_results)} papers"))
        return all_results

    def _fetch_crossref_fallback(
        self,
        max_results: int,
        search_terms: List[str],
    ) -> List[Dict[str, Any]]:
        """Fetch formal journal metadata when OpenAlex is temporarily rate-limited.

        Crossref is only a metadata fallback: records still pass through the
        same scope and Q1/Q2 whitelist gate during normalization.
        """
        settings = self._source_config.get("crossref_fallback", {})
        if not isinstance(settings, dict) or not settings.get("enabled", False):
            return []
        terms = search_terms or self._crossref_default_terms()
        if not terms or max_results <= 0:
            return []

        rows = min(100, max(1, int(settings.get("rows_per_query", 50))))
        date_from = str(settings.get("from_publication_date") or "").strip()
        mailto = str(settings.get("mailto") or "").strip()
        user_agent = "daily-arxiv/1.0"
        if mailto:
            user_agent += f" (mailto:{mailto})"

        records: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for term in terms:
            params = {
                "query.title": term,
                "filter": ",".join(
                    value for value in [
                        "type:journal-article",
                        f"from-pub-date:{date_from}" if date_from else "",
                    ] if value
                ),
                "rows": str(rows),
                "select": (
                    "DOI,title,container-title,ISSN,type,published,"
                    "published-print,published-online,author,publisher,"
                    "is-referenced-by-count,URL"
                ),
            }
            try:
                response = self.client.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers={"User-Agent": user_agent},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                self.logger.warning(self.fetcher_text(
                    f"Crossref 兜底检索失败: {exc}",
                    f"Crossref fallback search failed: {exc}",
                ))
                continue

            payload = response.json()
            items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
            for work in items:
                if not isinstance(work, dict):
                    continue
                record = self._crossref_work_to_record(work)
                key = str(record.get("doi") or record.get("id") or "").casefold()
                if not key or key in seen or self._is_survey(record) or self._is_off_topic(record):
                    continue
                seen.add(key)
                records.append(record)
                if len(records) >= max_results:
                    return records
        return records

    def _crossref_default_terms(self) -> List[str]:
        configured = self._source_config.get("search_terms", [])
        if isinstance(configured, list):
            return [str(item).strip() for item in configured if str(item).strip()]
        return []

    @staticmethod
    def _crossref_work_to_record(work: Dict[str, Any]) -> Dict[str, Any]:
        doi = str(work.get("DOI") or "").strip()
        title = _first_text(work.get("title"))
        journal_name = _first_text(work.get("container-title"))
        issns = _string_values(work.get("ISSN"))
        authors = [
            " ".join(filter(None, [
                str(item.get("given") or "").strip(),
                str(item.get("family") or "").strip(),
            ])).strip()
            for item in work.get("author", []) if isinstance(item, dict)
        ]
        entry_url = str(work.get("URL") or (f"https://doi.org/{doi}" if doi else "")).strip()
        return {
            "id": doi or entry_url,
            "title": title,
            "authors": [author for author in authors if author],
            "abstract": "",
            "categories": [],
            "published": _crossref_date(work),
            "entry_url": entry_url,
            "pdf_url": entry_url,
            "doi": doi,
            "source_name": "Crossref",
            "source_record_provider": "crossref_fallback",
            "fetched_at": datetime.now().isoformat(),
            "citation_count": int(work.get("is-referenced-by-count") or 0),
            "publication_type": str(work.get("type") or ""),
            "journal_name": journal_name,
            "venue": journal_name,
            "journal_issn_l": issns[0] if issns else "",
            "journal_issn": issns,
            "journal_publisher": str(work.get("publisher") or ""),
        }

    def fetch_range(
        self,
        date_from: str,
        date_to: str,
        *,
        max_results: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch one publication-date partition using cursor pagination.

        Unlike ``fetch``, this method never writes the live paper snapshot. It
        is intended for the resumable historical corpus builder.
        """
        limit = max(1, int(
            max_results
            or self._source_config.get("backfill_max_results_per_month", 500)
        ))
        query = str(self._source_config.get("topic_query") or "").strip()
        filters = [
            f"from_publication_date:{date_from}",
            f"to_publication_date:{date_to}",
        ]
        concept_id = str(
            self._source_config.get("backfill_concept_id", "C89227174") or ""
        ).strip()
        if concept_id:
            filters.append(f"concepts.id:{concept_id}")
        params = {
            "search": query,
            "sort": str(self._source_config.get("sort", "publication_date:asc")),
            "per_page": str(min(100, max(1, self.per_page))),
            "select": ",".join(self.select_fields),
            "filter": ",".join(filters),
            "cursor": "*",
        }
        headers = {"api-key": self.api_key} if self.api_key else {}
        results: List[Dict[str, Any]] = []
        seen: set[str] = set()
        while params.get("cursor") and len(results) < limit:
            response = self.client.get(
                f"{self.base_url}/works", params=params, headers=headers
            )
            response.raise_for_status()
            payload = response.json()
            for work in payload.get("results", []):
                record = self._work_to_record(work)
                key = str(record.get("openalex_id") or record.get("id") or "")
                if not key or key in seen or self._is_survey(record) or self._is_off_topic(record):
                    continue
                seen.add(key)
                results.append(record)
                if len(results) >= limit:
                    break
            next_cursor = str(payload.get("meta", {}).get("next_cursor") or "")
            if not next_cursor or next_cursor == params.get("cursor"):
                break
            params["cursor"] = next_cursor
        return results

    def _fetch_by_concepts(self, max_results: int) -> List[Dict[str, Any]]:
        from datetime import timedelta

        recent_days = int(self._source_config.get("recent_days", 180))
        date_from = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d")

        topic_query = self._source_config.get("topic_query") or (
            '"peer-to-peer energy trading" OR "P2P energy trading" OR '
            '"peer-to-peer electricity market" OR "peer-to-peer electricity trading" OR '
            '"peer-to-peer energy market" OR "P2P electricity market"'
        )

        # electric power system concept keeps results inside the energy domain,
        # avoiding generic peer-to-peer networking / file-sharing papers
        filters = [f"from_publication_date:{date_from}", "concepts.id:C89227174"]
        sort = self._source_config.get("sort", "publication_date:desc")

        params = {
            "search": topic_query,
            "sort": sort,
            "per_page": str(self.per_page),
            "select": ",".join(self.select_fields),
            "filter": ",".join(filters),
        }

        self.logger.info(self.fetcher_text(
            f"OpenAlex 检索: P2P 市场交易 (近 {recent_days} 天, 自 {date_from})...",
            f"OpenAlex search: P2P market trading (last {recent_days} days, since {date_from})..."
        ))

        results: List[Dict[str, Any]] = []
        seen_titles: set = set()

        def _accept(record: Dict[str, Any]) -> bool:
            if self._is_survey(record):
                return False
            if self._is_off_topic(record):
                return False
            key = self._title_key(record.get("title", ""))
            if not key or key in seen_titles:
                return False
            seen_titles.add(key)
            return True

        works = self._search_works(params)
        for work in works:
            record = self._work_to_record(work)
            if _accept(record):
                results.append(record)
            if len(results) >= max_results:
                break

        # Fallback: if power-system concept filter is too strict, retry without it
        if not results:
            self.logger.info(self.fetcher_text(
                f"未命中, 放宽概念限制重试 (近 {recent_days} 天)...",
                f"No hits, retrying without concept filter (last {recent_days} days)..."
            ))
            params["filter"] = f"from_publication_date:{date_from}"
            for work in self._search_works(params):
                record = self._work_to_record(work)
                if _accept(record):
                    results.append(record)
                if len(results) >= max_results:
                    break

        return results

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return normalize_paper_records(records, self.source_name, self.config)

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
        raw_terms = self._source_config.get("search_terms", [])
        if raw_terms:
            return [str(t).strip() for t in raw_terms if str(t).strip()]

        # Build one query: intersect all keyword groups by chaining filters
        keyword_groups = self.config.get("keyword_groups", []) if isinstance(self.config, dict) else []
        if not keyword_groups:
            tracking = self.config.get("tracking_topics", []) if isinstance(self.config, dict) else []
            if tracking:
                return [" ".join(str(t).strip() for t in tracking if str(t).strip())]
            return []
        return ["__concept_filter__"]  # signal to use concept-based filtering

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
        arxiv_id = extract_arxiv_id(ids.get("arxiv"))
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

        record = {
            "id": arxiv_id or work.get("id", "").split("/")[-1],
            "title": work.get("display_name") or work.get("title", ""),
            "authors": authors,
            "abstract": "",
            "categories": [t for t in topics[:3]],
            "primary_category": topics[0] if topics else "",
            "published": work.get("publication_date") or work.get("publication_year", ""),
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
        return enrich_openalex_venue_metadata(record, work)

    @staticmethod
    def _bracket(cites: int) -> str:
        if cites >= 100:
            return "hot"
        if cites >= 25:
            return "high"
        if cites >= 5:
            return "notable"
        return ""

    @staticmethod
    def _is_survey(record: dict) -> bool:
        title = str(record.get("title", "")).lower()
        survey_words = ["survey", "review", "comprehensive review", "state-of-the-art",
                        "state of the art", "overview", "taxonomy", "bibliometric",
                        "systematic literature review", "meta-analysis"]
        for w in survey_words:
            if w in title:
                return True
        return False

    @staticmethod
    def _is_off_topic(record: dict) -> bool:
        """Drop peer-to-peer papers that are not about energy/electricity trading."""
        title = str(record.get("title", "")).lower()
        topics = " ".join(str(t).lower() for t in record.get("openalex_topics", []))
        concepts = " ".join(str(c).lower() for c in record.get("openalex_concepts", []))
        haystack = f"{title} {topics} {concepts}"

        # Must touch the energy / electricity / grid domain at all
        energy_words = ["energy", "electricity", "power", "grid", "microgrid",
                        "renewable", "carbon", "battery", "voltage", "load",
                        "demand response", "prosumer", "der", "photovoltaic", "ev"]
        if not any(w in haystack for w in energy_words):
            return True

        # Explicitly exclude non-energy peer-to-peer domains
        off_words = ["data center", "cloud service", "file sharing", "blockchain network throughput",
                     "video streaming", "content delivery", "cryptocurrency mining"]
        if any(w in title for w in off_words):
            return True
        return False

    @staticmethod
    def _title_key(title: str) -> str:
        import re
        key = str(title or "").lower().strip()
        key = re.sub(r"[^a-z0-9 ]", "", key)
        key = re.sub(r"\s+", " ", key)
        return key


def _is_rate_limited(error: httpx.HTTPStatusError) -> bool:
    """Return whether an HTTP error represents a retry-later source limit."""
    return error.response.status_code == 429


def _first_text(value: Any) -> str:
    values = _string_values(value)
    return values[0] if values else ""


def _string_values(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _crossref_date(work: Dict[str, Any]) -> str:
    """Extract a stable ISO-like publication date from a Crossref record."""
    for field in ("published", "published-print", "published-online"):
        payload = work.get(field)
        if not isinstance(payload, dict):
            continue
        parts = payload.get("date-parts")
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
            continue
        values = parts[0]
        if not values:
            continue
        try:
            year = int(values[0])
            if len(values) == 1:
                return f"{year:04d}"
            month = int(values[1])
            if len(values) == 2:
                return f"{year:04d}-{month:02d}"
            return f"{year:04d}-{month:02d}-{int(values[2]):02d}"
        except (TypeError, ValueError):
            continue
    return ""


def _unique_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep the first record for each DOI or provider identifier."""
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        key = str(record.get("doi") or record.get("id") or "").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique
