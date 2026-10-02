"""Industry report collection and structured trend extraction."""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.models.document_schema import SourceType, create_document
from src.summarizer.llm_factory import LLMClientFactory
from src.utils import save_json

from .rss_adapter import RSSSourceAdapter
from .structured_metadata import clean_optional, parse_json_object, string_list, unique


class IndustryReportSourceAdapter(RSSSourceAdapter):
    """Collect configured report feeds and normalize industry information."""

    source_name = "industry_report"

    def __init__(self, config: Dict[str, Any], llm_client: Any = None):
        self._llm_client = llm_client
        super().__init__(config)
        self._feed_config = {
            str(item.get("url", "")): item
            for item in self.source_config.get("feeds", [])
            if isinstance(item, dict)
        }

    @property
    def source_config(self) -> Dict[str, Any]:
        sources = self.config.get("sources", {}) if isinstance(self.config, dict) else {}
        value = sources.get("industry_report", {}) if isinstance(sources, dict) else {}
        return value if isinstance(value, dict) else {}

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map report entries and extracted trends into the unified schema."""
        documents = []
        for record in records:
            if not str(record.get("title", "")).strip():
                continue
            feed_config = self._feed_config.get(str(record.get("feed_url", "")), {})
            standard = self._extract_standard_fields(record, feed_config)
            insights = self._extract_llm_insights(record, standard)
            topic_directions = unique(
                standard["topic_directions"] + string_list(insights.get("topic_directions"))
            )
            keywords = unique(
                standard["keywords"] + string_list(insights.get("keywords")) + topic_directions
            )
            document = create_document(
                SourceType.INDUSTRY_REPORT,
                id=f"industry_report:{record['dedup_key']}",
                source_name=standard["institution"],
                title=str(record["title"]),
                summary=str(record.get("summary", "")),
                authors_or_orgs=[standard["institution"]],
                published_at=str(record.get("published_at", "")),
                collected_at=str(record.get("collected_at", "")),
                url=str(record.get("url", "")),
                raw_text=str(record.get("content", "")),
                keywords=keywords,
                tags=topic_directions,
                research_direction=topic_directions,
                region=standard["region"],
                institution=standard["institution"],
                report_type=standard["report_type"],
                topic_directions=topic_directions,
                industry_progress=clean_optional(insights.get("industry_progress")),
                trend_assessment=clean_optional(insights.get("trend_assessment")),
                provenance={
                    "collected_via": "industry_report_adapter",
                    "source_record_id": str(record.get("entry_id", "")),
                    "fetch_url": str(record.get("feed_url", "")),
                    "metadata": {
                        "dedup_key": record["dedup_key"],
                        "llm_extracted": bool(insights),
                    },
                },
            )
            documents.append(document.to_dict())
        return documents

    def _configured_feeds(self) -> List[Dict[str, Any]]:
        """Leave HTML report listings to the report-specific collector."""
        return [
            item
            for item in self.source_config.get("feeds", [])
            if isinstance(item, dict) and str(item.get("format", "rss")).lower() != "html"
        ]

    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Collect RSS/Atom and configured Chinese industry-report listings."""
        feed_kwargs = dict(kwargs)
        feed_kwargs["save_snapshot"] = False
        feed_kwargs["persist_state"] = False
        feed_records = super().fetch(**feed_kwargs)
        records = feed_records + self._fetch_html_sources()
        self._prune_seen()
        if records:
            self.save_raw_snapshot(records)
        save_json(self.state, self.state_path)
        return records

    def _fetch_html_sources(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        now = self._now()
        sources = [
            item
            for item in self.source_config.get("feeds", [])
            if isinstance(item, dict) and str(item.get("format", "rss")).lower() == "html"
        ]
        for source in sources:
            source_url = str(source["url"]).strip()
            source_state = self.state["feeds"].setdefault(source_url, {})
            headers = {"User-Agent": self.source_config.get("user_agent", "daily-arxiv/1.0")}
            if source_state.get("etag"):
                headers["If-None-Match"] = source_state["etag"]
            if source_state.get("last_modified"):
                headers["If-Modified-Since"] = source_state["last_modified"]
            try:
                response = self.client.get(source_url, headers=headers)
                if response.status_code == 304:
                    source_state.update(checked_at=now, last_success_at=now, last_error='')
                    continue
                response.raise_for_status()
            except httpx.HTTPError as exc:
                source_state.update({"checked_at": now, "last_error": str(exc)})
                self.logger.warning("Industry report page fetch failed for %s: %s", source_url, exc)
                continue

            source_state.update({
                "etag": response.headers.get("ETag", source_state.get("etag", "")),
                "last_modified": response.headers.get(
                    "Last-Modified", source_state.get("last_modified", "")
                ),
                "checked_at": now,
                "last_success_at": now,
                "last_error": "",
            })
            soup = BeautifulSoup(response.content, "html.parser")
            item_selector = str(source.get("item_selector", "a[href]"))
            items = soup.select(item_selector)
            if not items:
                message = f"selector matched no items: {item_selector}"
                source_state["last_error"] = message
                self.logger.warning("Industry report parse failed for %s: %s", source_url, message)
                continue
            for item in items[: int(source.get("max_entries", 50))]:
                link = item.select_one(str(source.get("link_selector", "a[href]")))
                if link is None and getattr(item, "name", None) == "a":
                    link = item
                if link is None or not link.get("href"):
                    continue
                title = self._clean_text(link.get("title") or link.get_text(" ", strip=True))
                if not self._matches_report_title(title, source):
                    continue
                url = self._canonical_url(urljoin(source_url, str(link["href"])))
                if not title or not url:
                    continue
                dedup_key = hashlib.sha256(f"{url}\n{title.casefold()}".encode("utf-8")).hexdigest()
                if dedup_key in self.state["seen"]:
                    continue
                date_node = (
                    item.select_one(str(source.get("date_selector", "")))
                    if source.get("date_selector")
                    else None
                )
                published_at = self._clean_text(
                    date_node.get_text(" ", strip=True) if date_node else ""
                )
                published_at = re.sub(r"^(日期|发布时间)\s*[：:]\s*", "", published_at)
                published_at = published_at.strip("() ").replace("/", "-")
                content = self._fetch_detail_text(url, source) if source.get("fetch_detail", True) else title
                content = content or title
                records.append({
                    "entry_id": url,
                    "title": title,
                    "url": url,
                    "author": str(source.get("institution") or source.get("name", "")),
                    "published_at": published_at,
                    "collected_at": now,
                    "summary": content[:1000],
                    "content": content,
                    "tags": self._string_list(source.get("tags")),
                    "source_name": str(source.get("name", "中国能源行业机构")),
                    "feed_title": str(source.get("name", "")),
                    "feed_url": source_url,
                    "region": source.get("region", "CN"),
                    "event_type": "industry_report",
                    "source_category": "industry_report",
                    "dedup_key": dedup_key,
                })
                self.state["seen"][dedup_key] = now
        return records

    def _fetch_detail_text(self, url: str, source: Dict[str, Any]) -> str:
        try:
            response = self.client.get(
                url,
                headers={"User-Agent": self.source_config.get("user_agent", "daily-arxiv/1.0")},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            selector = str(source.get("detail_content_selector", "article, .article-content"))
            content_node = soup.select_one(selector)
            return self._clean_text(content_node.get_text(" ", strip=True)) if content_node else ""
        except httpx.HTTPError as exc:
            self.logger.warning("Industry report detail fetch failed for %s: %s", url, exc)
            return ""

    @classmethod
    def _matches_report_title(cls, title: str, source: Dict[str, Any]) -> bool:
        include = cls._string_list(source.get("title_keywords_any"))
        exclude = cls._string_list(source.get("title_keywords_exclude"))
        lowered = title.casefold()
        if exclude and any(term.casefold() in lowered for term in exclude):
            return False
        return bool(title) and (not include or any(term.casefold() in lowered for term in include))

    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {"source": self.source_name, "collected_at": self._now(), "records": records}
        save_json(payload, str(self.snapshot_dir / f"industry_report_{timestamp}.json"))
        save_json(payload, str(self.snapshot_dir / "latest.json"))

    def _extract_standard_fields(
        self, record: Dict[str, Any], feed_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        text = f"{record.get('title', '')} {record.get('content', '')}"
        lowered = text.casefold()
        institution = str(
            feed_config.get("institution")
            or record.get("source_name")
            or "Unknown report institution"
        ).strip()
        topics = string_list(feed_config.get("topic_directions"))
        for topic in self.config.get("tracking_topics", []):
            if str(topic).casefold() in lowered:
                topics.append(str(topic))
        for group in self.config.get("keyword_groups", []):
            if not isinstance(group, dict):
                continue
            if any(str(term).casefold() in lowered for term in group.get("terms", [])):
                topics.append(str(group.get("name", "")))
        return {
            "institution": institution,
            "report_type": str(
                feed_config.get("report_type") or self._infer_report_type(text)
            ),
            "region": str(
                feed_config.get("region")
                or record.get("region")
                or next(iter(self.source_config.get("regions", [])), "CN")
            ),
            "topic_directions": unique(topics),
            "keywords": unique(string_list(feed_config.get("keywords")) + list(record.get("tags", []))),
        }

    def _extract_llm_insights(
        self, record: Dict[str, Any], standard: Dict[str, Any]
    ) -> Dict[str, Any]:
        extraction_config = self.source_config.get("llm_extraction", {})
        if not extraction_config.get("enabled", True):
            return {}
        try:
            if self._llm_client is None:
                self._llm_client = LLMClientFactory.create_client(self.config)
            prompt = f"""Extract structured industry information from the report below.
Return strict JSON only with keys: industry_progress (string),
trend_assessment (string), topic_directions (array of strings),
keywords (array of strings). Distinguish reported facts from forecasts.

Known metadata: {json.dumps(standard, ensure_ascii=False)}
Title: {record.get('title', '')}
Text: {record.get('content', '')[:12000]}
"""
            response = self._llm_client.generate(
                prompt,
                system_prompt="You extract concise, evidence-grounded industry report information.",
                max_tokens=int(extraction_config.get("max_tokens", 900)),
            )
            return parse_json_object(response)
        except Exception as exc:
            self.logger.warning("Industry report LLM extraction failed for %s: %s", record.get("title"), exc)
            return {}

    @staticmethod
    def _infer_report_type(text: str) -> str:
        lowered = text.casefold()
        candidates = [
            ("market_outlook", ["market outlook", "市场展望"]),
            ("forecast", ["forecast", "预测"]),
            ("white_paper", ["white paper", "whitepaper", "白皮书"]),
            ("technology_report", ["technology report", "技术报告"]),
            ("survey", ["survey", "调研"]),
            ("annual_report", ["annual report", "年度报告"]),
        ]
        for report_type, terms in candidates:
            if any(term in lowered for term in terms):
                return report_type
        return "industry_report"
