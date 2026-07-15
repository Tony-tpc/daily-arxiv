"""Policy document collection and structured policy metadata extraction."""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.models.document_schema import SourceType, create_document
from src.summarizer.llm_factory import LLMClientFactory
from src.utils import save_json

from .rss_adapter import RSSSourceAdapter
from .structured_metadata import clean_optional, parse_json_object, string_list, unique


def is_policy_in_scope(
    record: Dict[str, Any],
    config: Dict[str, Any],
    feed_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Keep policy records whose titles match the configured energy boundary."""
    settings = config.get("sources", {}).get("policy", {})
    if not isinstance(settings, dict):
        return True
    feed_config = feed_config or {}
    include = unique(
        string_list(settings.get("title_keywords_any"))
        + string_list(feed_config.get("title_keywords_any"))
    )
    exclude = unique(
        string_list(settings.get("title_keywords_exclude"))
        + string_list(feed_config.get("title_keywords_exclude"))
    )
    title = str(record.get("title") or "").casefold()
    if exclude and any(term.casefold() in title for term in exclude):
        return False
    return not include or any(term.casefold() in title for term in include)


class PolicySourceAdapter(RSSSourceAdapter):
    """Collect configured policy feeds and normalize entries as policy documents."""

    source_name = "policy"

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
        value = sources.get("policy", {}) if isinstance(sources, dict) else {}
        return value if isinstance(value, dict) else {}

    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract deterministic and optional LLM policy fields into the schema."""
        documents = []
        for record in records:
            if not str(record.get("title", "")).strip():
                continue
            feed_config = self._feed_config.get(str(record.get("feed_url", "")), {})
            if not is_policy_in_scope(record, self.config, feed_config):
                continue
            standard = self._extract_standard_fields(record, feed_config)
            insights = self._extract_llm_insights(record, standard)
            technology_directions = string_list(insights.get("technology_directions"))
            impact_areas = unique(
                standard["impact_areas"] + string_list(insights.get("impact_areas"))
            )
            document = create_document(
                SourceType.POLICY,
                id=f"policy:{record['dedup_key']}",
                source_name=standard["issuing_body"],
                title=str(record["title"]),
                summary=str(record.get("summary", "")),
                authors_or_orgs=[standard["issuing_body"]],
                published_at=str(record.get("published_at", "")),
                collected_at=str(record.get("collected_at", "")),
                url=str(record.get("url", "")),
                raw_text=str(record.get("content", "")),
                keywords=unique(list(record.get("tags", [])) + impact_areas),
                tags=unique(impact_areas + [standard["document_type"], standard["policy_strength"]]),
                research_direction=technology_directions,
                importance_score=self._strength_score(standard["policy_strength"]),
                issuing_body=standard["issuing_body"],
                policy_level=standard["policy_level"],
                region=standard["region"],
                effective_date=standard["effective_date"],
                document_type=standard["document_type"],
                impact_areas=impact_areas,
                policy_strength=standard["policy_strength"],
                core_policy_direction=clean_optional(insights.get("core_policy_direction")),
                technology_directions=technology_directions,
                potential_impact=clean_optional(insights.get("potential_impact")),
                provenance={
                    "collected_via": "policy_adapter",
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
        """Leave HTML policy pages to the policy-specific collector."""
        return [
            item
            for item in self.source_config.get("feeds", [])
            if isinstance(item, dict) and str(item.get("format", "rss")).lower() != "html"
        ]

    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Collect RSS/Atom and configured official HTML policy listings."""
        feed_kwargs = dict(kwargs)
        feed_kwargs["save_snapshot"] = False
        feed_kwargs["persist_state"] = False
        feed_records = super().fetch(**feed_kwargs)
        html_records = self._fetch_html_sources()
        records = feed_records + html_records
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
                    source_state["checked_at"] = now
                    continue
                response.raise_for_status()
            except httpx.HTTPError as exc:
                source_state.update({"checked_at": now, "last_error": str(exc)})
                self.logger.warning("Policy page fetch failed for %s: %s", source_url, exc)
                continue

            source_state.update(
                {
                    "etag": response.headers.get("ETag", source_state.get("etag", "")),
                    "last_modified": response.headers.get(
                        "Last-Modified", source_state.get("last_modified", "")
                    ),
                    "checked_at": now,
                    "last_success_at": now,
                    "last_error": "",
                }
            )
            soup = BeautifulSoup(response.content, "html.parser")
            item_selector = str(source.get("item_selector", "a[href]"))
            items = soup.select(item_selector)
            if not items:
                message = f"selector matched no items: {item_selector}"
                source_state["last_error"] = message
                self.logger.warning("Policy page parse failed for %s: %s", source_url, message)
                continue
            for item in items[: int(source.get("max_entries", 50))]:
                link = item.select_one(str(source.get("link_selector", "a[href]")))
                if link is None and getattr(item, "name", None) == "a":
                    link = item
                if link is None or not link.get("href"):
                    continue
                title = self._clean_text(link.get("title") or link.get_text(" ", strip=True))
                url = self._canonical_url(urljoin(source_url, str(link["href"])))
                if not title or not url:
                    continue
                if not is_policy_in_scope({"title": title}, self.config, source):
                    continue
                dedup_key = hashlib.sha256(f"{url}\n{title.casefold()}".encode("utf-8")).hexdigest()
                if dedup_key in self.state["seen"]:
                    continue
                date_node = (
                    item.select_one(str(source.get("date_selector", "")))
                    if source.get("date_selector")
                    else None
                )
                published_at = self._clean_text(date_node.get_text(" ", strip=True) if date_node else "")
                published_at = published_at.strip("() ").replace("/", "-")
                content = self._fetch_detail_text(url, source) if source.get("fetch_detail", True) else title
                content = content or title
                records.append(
                    {
                        "entry_id": url,
                        "title": title,
                        "url": url,
                        "author": str(source.get("issuing_body") or source.get("name", "")),
                        "published_at": published_at,
                        "collected_at": now,
                        "summary": content[:1000],
                        "content": content,
                        "tags": string_list(source.get("tags")),
                        "source_name": str(source.get("name", "中国政策来源")),
                        "feed_title": str(source.get("name", "")),
                        "feed_url": source_url,
                        "region": source.get("region", "CN"),
                        "event_type": "policy",
                        "source_category": "government_policy",
                        "dedup_key": dedup_key,
                    }
                )
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
            selector = str(source.get("detail_content_selector", "article"))
            content_node = soup.select_one(selector)
            if content_node is None:
                return ""
            return self._clean_text(content_node.get_text(" ", strip=True))
        except httpx.HTTPError as exc:
            self.logger.warning("Policy detail fetch failed for %s: %s", url, exc)
            return ""

    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {"source": self.source_name, "collected_at": self._now(), "records": records}
        save_json(payload, str(self.snapshot_dir / f"policy_{timestamp}.json"))
        save_json(payload, str(self.snapshot_dir / "latest.json"))

    def _extract_standard_fields(
        self, record: Dict[str, Any], feed_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        text = f"{record.get('title', '')} {record.get('content', '')}"
        issuing_body = str(
            feed_config.get("issuing_body")
            or record.get("source_name")
            or "Unknown policy issuer"
        ).strip()
        document_type = str(feed_config.get("document_type") or self._infer_document_type(text))
        strength = str(feed_config.get("policy_strength") or self._infer_strength(text, document_type))
        impact_areas = string_list(feed_config.get("impact_areas"))
        impact_areas.extend(str(tag) for tag in record.get("tags", []))
        lowered = text.casefold()
        for topic in self.config.get("tracking_topics", []):
            if str(topic).casefold() in lowered:
                impact_areas.append(str(topic))
        for group in self.config.get("keyword_groups", []):
            if not isinstance(group, dict):
                continue
            if any(str(term).casefold() in lowered for term in group.get("terms", [])):
                impact_areas.append(str(group.get("name", "")))
        return {
            "issuing_body": issuing_body,
            "document_type": document_type,
            "published_at": str(record.get("published_at", "")),
            "effective_date": str(
                feed_config.get("effective_date") or self._infer_effective_date(text)
            ),
            "impact_areas": unique(impact_areas),
            "policy_strength": strength,
            "policy_level": str(feed_config.get("policy_level", "unspecified")),
            "region": str(
                feed_config.get("region")
                or record.get("region")
                or next(iter(self.source_config.get("regions", [])), "CN")
            ),
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
            prompt = f"""Extract policy intelligence from the document below.
Return strict JSON only with keys: core_policy_direction (string),
technology_directions (array of strings), potential_impact (string),
impact_areas (array of strings). Do not invent facts.

Known metadata: {json.dumps(standard, ensure_ascii=False)}
Title: {record.get('title', '')}
Text: {record.get('content', '')[:12000]}
"""
            response = self._llm_client.generate(
                prompt,
                system_prompt="You extract concise, evidence-grounded policy intelligence.",
                max_tokens=int(extraction_config.get("max_tokens", 900)),
            )
            return parse_json_object(response)
        except Exception as exc:
            self.logger.warning("Policy LLM extraction failed for %s: %s", record.get("title"), exc)
            return {}

    @staticmethod
    def _infer_document_type(text: str) -> str:
        lowered = text.casefold()
        candidates = [
            ("regulation", ["regulation", "rule", "条例", "规定"]),
            ("law", [" act ", " law ", "法案", "法律"]),
            ("order", ["order", "命令", "令"]),
            ("strategy", ["strategy", "roadmap", "战略", "路线图"]),
            ("plan", ["plan", "规划", "计划"]),
            ("guideline", ["guideline", "guidance", "指南", "指导意见"]),
            ("notice", ["notice", "announcement", "通知", "公告"]),
        ]
        for document_type, terms in candidates:
            if any(term in lowered for term in terms):
                return document_type
        return "policy_document"

    @staticmethod
    def _infer_strength(text: str, document_type: str) -> str:
        lowered = text.casefold()
        if document_type in {"law", "regulation", "order"} or any(
            term in lowered for term in ["shall", "must", "mandatory", "应当", "必须"]
        ):
            return "high"
        if document_type in {"strategy", "plan", "guideline"}:
            return "medium"
        return "low"

    @staticmethod
    def _infer_effective_date(text: str) -> str:
        patterns = [
            r"(?:effective(?:\s+date|\s+from)?|takes effect(?: on)?)[：:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(?:生效日期|自)[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _strength_score(value: str) -> float:
        return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(value, 0.3)
