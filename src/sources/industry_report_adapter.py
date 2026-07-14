"""Industry report collection and structured trend extraction."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.models.document_schema import SourceType, create_document
from src.summarizer.llm_factory import LLMClientFactory
from src.utils import save_json

from .rss_adapter import RSSSourceAdapter
from .structured_metadata import clean_optional, parse_json_object, string_list, unique


class IndustryReportSourceAdapter(RSSSourceAdapter):
    """Collect configured report feeds and normalize industry intelligence."""

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
            prompt = f"""Extract industry intelligence from the report below.
Return strict JSON only with keys: industry_progress (string),
trend_assessment (string), topic_directions (array of strings),
keywords (array of strings). Distinguish reported facts from forecasts.

Known metadata: {json.dumps(standard, ensure_ascii=False)}
Title: {record.get('title', '')}
Text: {record.get('content', '')[:12000]}
"""
            response = self._llm_client.generate(
                prompt,
                system_prompt="You extract concise, evidence-grounded industry report intelligence.",
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
