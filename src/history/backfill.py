"""Resumable, event-dated historical corpus backfill."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.sources.industry_report_adapter import IndustryReportSourceAdapter
from src.sources.openalex_search_adapter import OpenAlexSearchAdapter
from src.sources.policy_adapter import PolicySourceAdapter, is_policy_in_scope
from src.sources.rss_adapter import RSSSourceAdapter, is_news_in_scope
from src.sources.paper_normalizer import is_excluded_paper
from src.sources.paper_quality import is_high_impact_paper


SOURCE_TYPES = {
    "openalex_search": "paper",
    "policy": "policy",
    "rss": "news",
    "industry_report": "industry_report",
}


@dataclass
class FetchResult:
    """Documents plus truthful coverage information for one period."""

    documents: List[Dict[str, Any]]
    status: str = "complete"
    errors: List[str] | None = None
    metadata: Dict[str, Any] | None = None


class HistoricalCorpus:
    """Portable monthly JSON corpus with atomic, idempotent writes."""

    def __init__(self, root: str | Path = "data/history"):
        self.root = Path(root)
        self.coverage_path = self.root / "coverage.json"

    def write_period(
        self,
        source_name: str,
        period: str,
        result: FetchResult,
    ) -> Path:
        source_type = SOURCE_TYPES[source_name]
        path = self.root / source_type / f"{period}.json"
        existing = self._load(path)
        documents = _merge_documents(
            existing.get("documents", []), result.documents
        )
        status = result.status
        errors = list(result.errors or [])
        if existing.get("status") == "complete" and status != "complete":
            status = "complete"
            errors = list(existing.get("errors", []))
        elif documents and status == "unavailable":
            status = "partial"
        payload = {
            "schema_version": "2.0",
            "source_name": source_name,
            "source_type": source_type,
            "period": period,
            "status": status,
            "errors": errors,
            "metadata": dict(result.metadata or {}),
            "document_count": len(documents),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "documents": documents,
        }
        self._atomic_write(path, payload)
        self._update_coverage(payload, path)
        return path

    def load_observations(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
    ) -> List[Dict[str, Any]]:
        observations: List[Dict[str, Any]] = []
        roots = [self.root / source_type] if source_type else [
            self.root / value for value in sorted(set(SOURCE_TYPES.values()))
        ]
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.glob("????-??.json")):
                payload = self._load(path)
                for document in payload.get("documents", []):
                    event_date = str(document.get("published_at") or "")[:10]
                    if date_from and event_date < date_from:
                        continue
                    if date_to and event_date > date_to:
                        continue
                    observations.append({
                        "snapshot_id": f"history:{payload.get('source_name')}:{payload.get('period')}",
                        "snapshot_date": str(payload.get("updated_at") or "")[:10],
                        "created_at": payload.get("updated_at", ""),
                        "document": document,
                    })
        return observations

    def load_coverage(self) -> Dict[str, Any]:
        return self._load(self.coverage_path)

    def _update_coverage(self, payload: Dict[str, Any], path: Path) -> None:
        coverage = self._load(self.coverage_path)
        entries = coverage.get("entries", {})
        key = f"{payload['source_name']}:{payload['period']}"
        entries[key] = {
            "source_name": payload["source_name"],
            "source_type": payload["source_type"],
            "period": payload["period"],
            "status": payload["status"],
            "document_count": payload["document_count"],
            "errors": payload["errors"],
            "location": path.as_posix(),
            "updated_at": payload["updated_at"],
        }
        statuses = [entry.get("status") for entry in entries.values()]
        self._atomic_write(self.coverage_path, {
            "schema_version": "2.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entry_count": len(entries),
            "status_counts": {
                status: statuses.count(status)
                for status in ("complete", "partial", "unavailable")
            },
            "entries": dict(sorted(entries.items())),
        })

    @staticmethod
    def _load(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, path)


class BackfillService:
    """Populate 24 months of papers and China-only non-paper sources."""

    def __init__(
        self,
        config: Dict[str, Any],
        *,
        corpus: HistoricalCorpus | None = None,
        fetchers: Dict[str, Callable[[date, date], FetchResult]] | None = None,
    ):
        self.config = copy.deepcopy(config)
        self.config.setdefault("sources", {}).setdefault("policy", {}).setdefault(
            "llm_extraction", {}
        )["enabled"] = False
        self.config["sources"].setdefault("industry_report", {}).setdefault(
            "llm_extraction", {}
        )["enabled"] = False
        root = self.config.get("analysis", {}).get(
            "history_directory", "data/history"
        )
        self.corpus = corpus or HistoricalCorpus(root)
        self.fetchers = fetchers or {}
        self.logger = logging.getLogger("daily_arxiv.history.backfill")

    def run(
        self,
        *,
        months: int = 24,
        as_of: str | date | None = None,
        sources: Iterable[str] | None = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        end = _as_date(as_of) if as_of else date.today()
        if end is None:
            raise ValueError(f"Invalid as_of date: {as_of}")
        periods = _month_periods(end, max(1, int(months)))
        selected = list(sources or SOURCE_TYPES)
        unknown = [name for name in selected if name not in SOURCE_TYPES]
        if unknown:
            raise ValueError(f"Unsupported backfill sources: {', '.join(unknown)}")

        completed = 0
        skipped = 0
        for source_name in selected:
            pending = [
                item for item in periods
                if force or not self._period_is_complete(source_name, item[0])
            ]
            skipped += len(periods) - len(pending)
            bulk_result: FetchResult | None = None
            if (
                pending
                and source_name != "openalex_search"
                and source_name not in self.fetchers
            ):
                try:
                    bulk_result = self._fetch_period(
                        source_name, pending[0][1], pending[-1][2]
                    )
                except Exception as exc:  # keep other sources/months progressing
                    self.logger.exception(
                        "Backfill failed for %s archive range", source_name
                    )
                    bulk_result = FetchResult([], "unavailable", [str(exc)])

            for period, period_start, period_end in pending:
                if bulk_result is not None:
                    result = FetchResult(
                        list(bulk_result.documents),
                        bulk_result.status,
                        list(bulk_result.errors or []),
                        dict(bulk_result.metadata or {}),
                    )
                else:
                    try:
                        fetcher = self.fetchers.get(source_name)
                        result = (
                            fetcher(period_start, period_end)
                            if fetcher
                            else self._fetch_period(
                                source_name, period_start, period_end
                            )
                        )
                    except Exception as exc:  # keep other months progressing
                        self.logger.exception(
                            "Backfill failed for %s %s", source_name, period
                        )
                        result = FetchResult([], "unavailable", [str(exc)])
                result.documents = [
                    document for document in result.documents
                    if _document_in_period(document, period_start, period_end)
                    and self._in_scope(document)
                ]
                self.corpus.write_period(source_name, period, result)
                completed += 1
        coverage = self.corpus.load_coverage()
        return {
            "schema_version": "2.0",
            "as_of": end.isoformat(),
            "months": len(periods),
            "sources": selected,
            "completed_periods": completed,
            "skipped_periods": skipped,
            "coverage": coverage,
        }

    def _period_is_complete(self, source_name: str, period: str) -> bool:
        entry = self.corpus.load_coverage().get("entries", {}).get(
            f"{source_name}:{period}", {}
        )
        return entry.get("status") == "complete"

    def _fetch_period(
        self, source_name: str, period_start: date, period_end: date
    ) -> FetchResult:
        if source_name == "openalex_search":
            adapter = OpenAlexSearchAdapter(self.config)
            raw = adapter.fetch_range(
                period_start.isoformat(), period_end.isoformat()
            )
            return FetchResult(
                adapter.normalize(raw),
                metadata={"transport": "openalex_cursor", "raw_count": len(raw)},
            )

        adapter: Any
        if source_name == "policy":
            adapter = PolicySourceAdapter(self.config)
        elif source_name == "rss":
            adapter = RSSSourceAdapter(self.config)
        else:
            adapter = IndustryReportSourceAdapter(self.config)
        collector = _HTMLArchiveCollector(self.config, source_name, adapter)
        raw, status, errors, metadata = collector.fetch(period_start, period_end)
        return FetchResult(adapter.normalize(raw), status, errors, metadata)

    def _in_scope(self, document: Dict[str, Any]) -> bool:
        source_type = str(document.get("source_type") or "")
        if source_type == "policy":
            return is_policy_in_scope(document, self.config)
        if source_type == "news":
            return is_news_in_scope(document, self.config)
        if source_type == "paper":
            return (
                not is_excluded_paper(document, self.config)
                and is_high_impact_paper(document, self.config)
            )
        searchable = " ".join([
            str(document.get("title") or ""),
            " ".join(str(value) for value in document.get("tags", [])),
            " ".join(str(value) for value in document.get("research_direction", [])),
        ]).casefold()
        excluded = [
            "robot arm", "robotic arm", "humanoid", "navigation",
            "机械臂", "机器人", "人形", "导航",
        ]
        return not any(term.casefold() in searchable for term in excluded)


class _HTMLArchiveCollector:
    """Config-driven archive reader used for Chinese policy/news/report sites."""

    def __init__(self, config: Dict[str, Any], source_name: str, adapter: Any):
        self.config = config
        self.source_name = source_name
        self.adapter = adapter
        settings = config.get("sources", {}).get(source_name, {})
        self.settings = settings if isinstance(settings, dict) else {}
        timeout = float(self.settings.get("request_timeout_seconds", 20))
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def fetch(
        self, period_start: date, period_end: date
    ) -> tuple[List[Dict[str, Any]], str, List[str], Dict[str, Any]]:
        feeds = self.settings.get("backfill_feeds") or [
            item for item in self.settings.get("feeds", [])
            if isinstance(item, dict) and str(item.get("format", "rss")).lower() == "html"
        ]
        records: List[Dict[str, Any]] = []
        errors: List[str] = []
        successful_feeds = 0
        attempted_pages = 0
        for source in feeds:
            source_records, source_errors, pages = self._fetch_source(
                source, period_start, period_end
            )
            attempted_pages += pages
            errors.extend(source_errors)
            if pages:
                successful_feeds += 1
            records.extend(source_records)
        if not feeds or not successful_feeds:
            status = "unavailable"
        elif errors or successful_feeds < len(feeds):
            status = "partial"
        else:
            status = "complete"
        return records, status, errors, {
            "transport": "china_html_archive",
            "feed_count": len(feeds),
            "successful_feeds": successful_feeds,
            "attempted_pages": attempted_pages,
            "raw_count": len(records),
        }

    def _fetch_source(
        self, source: Dict[str, Any], period_start: date, period_end: date
    ) -> tuple[List[Dict[str, Any]], List[str], int]:
        records: List[Dict[str, Any]] = []
        errors: List[str] = []
        pages = 0
        for page_url in _archive_page_urls(source):
            try:
                response = self.client.get(page_url, headers={
                    "User-Agent": self.settings.get("user_agent", "daily-arxiv/2.0")
                })
                response.raise_for_status()
            except httpx.HTTPError as exc:
                errors.append(f"{page_url}: {exc}")
                break
            pages += 1
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(str(source.get("item_selector", "li")))
            if not items:
                errors.append(f"{page_url}: selector matched no items")
                break
            page_dates: List[date] = []
            for item in items:
                record = self._item_to_record(item, page_url, source)
                if not record:
                    continue
                published = _as_date(record.get("published_at"))
                if published:
                    page_dates.append(published)
                if published and period_start <= published <= period_end:
                    records.append(record)
            if page_dates and min(page_dates) < period_start:
                break
        return records, errors, pages

    def _item_to_record(
        self, item: Any, page_url: str, source: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        link = item.select_one(str(source.get("link_selector", "a[href]")))
        if link is None and getattr(item, "name", None) == "a":
            link = item
        if link is None or not link.get("href"):
            return None
        title = " ".join(
            str(link.get("title") or link.get_text(" ", strip=True)).split()
        )
        url = urljoin(page_url, str(link.get("href")))
        date_node = item.select_one(str(source.get("date_selector", ""))) \
            if source.get("date_selector") else None
        date_text = date_node.get_text(" ", strip=True) if date_node else item.get_text(" ", strip=True)
        published_at = _extract_date(date_text) or _extract_date(url)
        if not title or not published_at:
            return None
        if self.source_name == "policy" and not is_policy_in_scope(
            {"title": title}, self.config, source
        ):
            return None
        if self.source_name == "industry_report" and not self.adapter._matches_report_title(title, source):
            return None
        dedup_key = hashlib.sha256(
            f"{url}\n{title.casefold()}".encode("utf-8")
        ).hexdigest()
        content = title
        if source.get("backfill_fetch_detail", False):
            content = self.adapter._fetch_detail_text(url, source) or title
        return {
            "entry_id": url,
            "title": title,
            "url": url,
            "author": str(
                source.get("issuing_body")
                or source.get("institution")
                or source.get("name", "")
            ),
            "published_at": published_at,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "summary": content[:1000],
            "content": content,
            "tags": list(source.get("tags") or []),
            "source_name": str(source.get("name") or "中国能源来源"),
            "feed_title": str(source.get("name") or ""),
            "feed_url": str(source.get("url") or page_url),
            "region": "CN",
            "event_type": SOURCE_TYPES[self.source_name],
            "source_category": source.get("source_category", SOURCE_TYPES[self.source_name]),
            "dedup_key": dedup_key,
        }


def _month_periods(end: date, months: int) -> List[tuple[str, date, date]]:
    periods = []
    year, month = end.year, end.month
    for offset in reversed(range(months)):
        absolute = year * 12 + month - 1 - offset
        period_year, zero_month = divmod(absolute, 12)
        period_month = zero_month + 1
        start = date(period_year, period_month, 1)
        next_absolute = absolute + 1
        next_year, next_zero_month = divmod(next_absolute, 12)
        next_start = date(next_year, next_zero_month + 1, 1)
        period_end = min(end, date.fromordinal(next_start.toordinal() - 1))
        periods.append((f"{period_year:04d}-{period_month:02d}", start, period_end))
    return periods


def _archive_page_urls(source: Dict[str, Any]) -> Iterable[str]:
    first = str(source.get("url") or "").strip()
    if first:
        yield first
    template = str(source.get("page_url_template") or "").strip()
    if not template:
        return
    start = int(source.get("page_start", 1))
    max_pages = max(1, int(source.get("max_pages", 30)))
    for page in range(start, start + max_pages):
        url = template.format(page=page)
        if url != first:
            yield url


def _extract_date(value: Any) -> str:
    text = str(value or "")
    match = re.search(
        r"(20\d{2})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})",
        text,
    )
    if not match:
        return ""
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return ""


def _merge_documents(
    existing: Iterable[Dict[str, Any]], incoming: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for document in [*existing, *incoming]:
        key = str(
            document.get("id") or document.get("canonical_url")
            or document.get("url") or document.get("title") or ""
        )
        if key:
            merged[key] = document
    return sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("published_at") or ""), str(item.get("id") or "")
        ),
    )


def _document_in_period(
    document: Dict[str, Any], period_start: date, period_end: date
) -> bool:
    published = _as_date(document.get("published_at"))
    return bool(published and period_start <= published <= period_end)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None
