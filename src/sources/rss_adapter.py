"""RSS and Atom source adapter with conditional requests and durable deduplication."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx

from src.models.document_schema import SourceType, create_document
from src.utils import load_json, save_json

from .base import BaseSourceAdapter
from .listing import parse_listing


def is_news_in_scope(record: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Exclude company updates while retaining system-level domestic energy news."""
    settings = config.get("sources", {}).get("rss", {})
    if not isinstance(settings, dict) or not settings.get(
        "exclude_enterprise_updates", False
    ):
        return True

    title = str(record.get("title") or "").casefold()
    if not title:
        return True
    strong_terms = _string_list(settings.get("enterprise_strong_exclude_keywords"))
    if any(term.casefold() in title for term in strong_terms):
        return False

    entity_terms = _string_list(settings.get("enterprise_entity_keywords"))
    action_terms = _string_list(settings.get("enterprise_update_keywords"))
    has_enterprise = any(term.casefold() in title for term in entity_terms)
    has_update = any(term.casefold() in title for term in action_terms)
    return not (has_enterprise and has_update)


def _string_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []


class RSSSourceAdapter(BaseSourceAdapter):
    """Collect standard RSS/Atom entries and normalize them as news documents."""

    source_name = "rss"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.timeout = float(self.source_config.get("request_timeout_seconds", 20))
        self.state_path = str(
            self.source_config.get("state_path", f"data/state/{self.source_name}.json")
        )
        self.snapshot_dir = Path(
            self.source_config.get("snapshot_dir", f"data/raw/{self.source_name}")
        )
        self.max_entries_per_feed = int(self.source_config.get("max_entries_per_feed", 100))
        self.max_seen_items = int(self.source_config.get("max_seen_items", 10000))
        self.state = load_json(self.state_path) or {"feeds": {}, "seen": {}}
        self.state.setdefault("feeds", {})
        self.state.setdefault("seen", {})
        self.client = httpx.Client(timeout=self.timeout, follow_redirects=True)

    @property
    def source_config(self) -> Dict[str, Any]:
        sources = self.config.get("sources", {}) if isinstance(self.config, dict) else {}
        value = sources.get("rss", {}) if isinstance(sources, dict) else {}
        return value if isinstance(value, dict) else {}

    def validate(self) -> None:
        feeds = self.source_config.get("feeds", [])
        if not isinstance(feeds, list) or not feeds:
            raise ValueError("RSS source requires at least one configured feed")
        urls = []
        for feed in feeds:
            if not isinstance(feed, dict) or not str(feed.get("name", "")).strip():
                raise ValueError("Each RSS feed requires a name")
            url = str(feed.get("url", "")).strip()
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"RSS feed requires an HTTP(S) URL: {url!r}")
            urls.append(url)
        if len(urls) != len(set(urls)):
            raise ValueError("RSS feed URLs must be unique")

    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch enabled feeds, honoring validators and skipping seen entries."""
        self.validate()
        records: List[Dict[str, Any]] = []
        now = self._now()

        for feed_config in self._configured_feeds():
            if not feed_config.get("enabled", True):
                continue
            feed_url = str(feed_config["url"]).strip()
            feed_state = self.state["feeds"].setdefault(feed_url, {})
            headers = {
                "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9",
                "User-Agent": self.source_config.get("user_agent", "daily-arxiv/1.0"),
            }
            if feed_state.get("etag"):
                headers["If-None-Match"] = feed_state["etag"]
            if feed_state.get("last_modified"):
                headers["If-Modified-Since"] = feed_state["last_modified"]

            try:
                response = self.client.get(feed_url, headers=headers)
                if response.status_code == 304:
                    feed_state.update(checked_at=now, last_success_at=now, last_error='')
                    continue
                response.raise_for_status()
            except httpx.HTTPError as exc:
                feed_state.update({"checked_at": now, "last_error": str(exc)})
                self.logger.warning("RSS fetch failed for %s: %s", feed_url, exc)
                continue

            try:
                parsed = ({'entries': parse_listing(response, feed_config), 'feed': {}}
                          if feed_config.get('format') in {'html', 'json'} else feedparser.parse(response.content))
            except (ValueError, TypeError, KeyError) as exc:
                feed_state.update(checked_at=now, last_error=str(exc))
                self.logger.warning('Listing parse failed for %s: %s', feed_url, exc)
                continue
            if parsed.get("bozo") and not parsed.get("entries"):
                message = str(parsed.get("bozo_exception", "invalid feed"))
                feed_state.update({"checked_at": now, "last_error": message})
                self.logger.warning("RSS parse failed for %s: %s", feed_url, message)
                continue

            feed_state.update(
                {
                    "etag": response.headers.get("ETag", feed_state.get("etag", "")),
                    "last_modified": response.headers.get(
                        "Last-Modified", feed_state.get("last_modified", "")
                    ),
                    "checked_at": now,
                    "last_success_at": now,
                    "last_error": "",
                }
            )
            feed_title = str(parsed.get("feed", {}).get("title", ""))
            for entry in parsed.get("entries", [])[: self.max_entries_per_feed]:
                record = self._raw_entry(entry, feed_config, feed_url, feed_title, now)
                if not record["title"]:
                    self.logger.warning("Skipping untitled RSS entry from %s", feed_url)
                    continue
                if not self._matches_content_filters(record, feed_config):
                    continue
                if feed_config.get('max_age_days'):
                    from src.hotspots.domain import timestamp
                    published = timestamp(record.get('published_at'))
                    cutoff = datetime.now(timezone.utc) - timedelta(days=int(feed_config['max_age_days']))
                    if published is not None and published <= cutoff:
                        continue
                dedup_key = record["dedup_key"]
                if dedup_key in self.state["seen"]:
                    continue
                if feed_config.get('fetch_detail') and not record['content']:
                    try:
                        from bs4 import BeautifulSoup
                        detail = self.client.get(record['url'])
                        detail.raise_for_status()
                        soup = BeautifulSoup(detail.content, 'html.parser')
                        body = soup.select_one(feed_config.get('detail_content_selector', 'article'))
                        if body is not None:
                            record['content'] = body.get_text(' ', strip=True)
                            record['summary'] = record['content'][:1000]
                    except httpx.HTTPError as exc:
                        self.logger.warning('Listing detail failed for %s: %s', record['url'], exc)
                    if not record['content']:
                        # Keep the item retryable and do not conditionally skip its listing.
                        feed_state.update(etag='', last_modified='', last_error='Article body unavailable')
                        continue
                self.state["seen"][dedup_key] = now
                records.append(record)

        self._prune_seen()
        if records and kwargs.get("save_snapshot", True):
            self.save_raw_snapshot(records)
        # Commit deduplication state only after the raw records are durable;
        # otherwise a snapshot failure could make entries disappear forever.
        if kwargs.get("persist_state", True):
            save_json(self.state, self.state_path)
        return records

    def _configured_feeds(self) -> List[Dict[str, Any]]:
        """Return feed-like sources handled by this transport."""
        return [item for item in self.source_config.get("feeds", []) if isinstance(item, dict)]

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map feed entries to the unified news schema."""
        documents = []
        for record in records:
            if not is_news_in_scope(record, self.config):
                continue
            source_name = record.get("source_name") or record.get("feed_title") or "RSS"
            authors = [value for value in [record.get("author"), source_name] if value]
            document = create_document(
                SourceType.NEWS,
                id=f"rss:{record['dedup_key']}",
                source_name=str(source_name),
                title=str(record.get("title", "")).strip(),
                summary=str(record.get("summary", "")),
                authors_or_orgs=list(dict.fromkeys(authors)),
                published_at=str(record.get("published_at", "")),
                collected_at=str(record.get("collected_at", "")),
                url=str(record.get("url", "")),
                raw_text=str(record.get("content", "")),
                keywords=list(record.get("tags", [])),
                media_name=str(source_name),
                region=record.get("region"),
                event_type=record.get("event_type") or "news",
                provenance={
                    "collected_via": "rss",
                    "source_record_id": str(record.get("entry_id", "")),
                    "fetch_url": str(record.get("feed_url", "")),
                    "metadata": {
                        "dedup_key": record["dedup_key"],
                        "source_category": record.get("source_category", ""),
                    },
                },
            )
            documents.append(document.to_dict())
        return documents

    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {"source": self.source_name, "collected_at": self._now(), "records": records}
        save_json(payload, str(self.snapshot_dir / f"{self.source_name}_{timestamp}.json"))
        save_json(payload, str(self.snapshot_dir / "latest.json"))

    def _raw_entry(
        self,
        entry: Dict[str, Any],
        feed_config: Dict[str, Any],
        feed_url: str,
        feed_title: str,
        collected_at: str,
    ) -> Dict[str, Any]:
        title = self._clean_text(entry.get("title", ""))
        url = self._canonical_url(entry.get("link", ""))
        dedup_key = hashlib.sha256(f"{url}\n{title.casefold()}".encode("utf-8")).hexdigest()
        content = entry.get("summary") or entry.get("description") or ""
        if entry.get("content"):
            content = "\n".join(str(part.get("value", "")) for part in entry["content"])
        clean_content = self._clean_text(content)
        tags = [str(tag.get("term", "")).strip() for tag in entry.get("tags", [])]
        return {
            "entry_id": str(entry.get("id") or entry.get("guid") or url or dedup_key),
            "title": title,
            "url": url,
            "author": self._clean_text(entry.get("author", "")),
            "published_at": self._entry_datetime(entry),
            "collected_at": collected_at,
            "summary": clean_content,
            "content": clean_content,
            "tags": [tag for tag in tags if tag],
            "source_name": str(feed_config.get("name") or feed_title or "RSS"),
            "feed_title": feed_title,
            "feed_url": feed_url,
            "region": feed_config.get("region"),
            "event_type": feed_config.get("event_type", "news"),
            "source_category": feed_config.get("source_category", ""),
            "dedup_key": dedup_key,
        }

    def _prune_seen(self) -> None:
        seen = self.state["seen"]
        if len(seen) <= self.max_seen_items:
            return
        retained = sorted(seen.items(), key=lambda item: item[1], reverse=True)[: self.max_seen_items]
        self.state["seen"] = dict(retained)

    def _matches_content_filters(
        self, record: Dict[str, Any], feed_config: Dict[str, Any]
    ) -> bool:
        """Apply optional source/feed keyword filters before an item enters state."""
        if self.source_name == "rss" and not is_news_in_scope(record, self.config):
            return False
        include = [
            *self._string_list(self.source_config.get("include_keywords")),
            *self._string_list(feed_config.get("include_keywords")),
        ]
        exclude = [
            *self._string_list(self.source_config.get("exclude_keywords")),
            *self._string_list(feed_config.get("exclude_keywords")),
        ]
        scope = str(
            feed_config.get("filter_scope")
            or self.source_config.get("filter_scope")
            or "all"
        ).lower()
        fields = [str(record.get("title", ""))]
        if scope != "title":
            fields.extend([
                str(record.get("content", "")),
                " ".join(str(tag) for tag in record.get("tags", [])),
            ])
        searchable = " ".join(fields).casefold()
        if exclude and any(term.casefold() in searchable for term in exclude):
            return False
        return not include or any(term.casefold() in searchable for term in include)

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        return _string_list(value)

    @staticmethod
    def _entry_datetime(entry: Dict[str, Any]) -> str:
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            parsed = entry.get(key)
            if parsed:
                return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
        return str(entry.get("published") or entry.get("updated") or "")

    @staticmethod
    def _canonical_url(value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        parts = urlsplit(raw)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))

    @staticmethod
    def _clean_text(value: Any) -> str:
        without_markup = re.sub(r"<[^>]+>", " ", str(value or ""))
        return re.sub(r"\s+", " ", html.unescape(without_markup)).strip()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
