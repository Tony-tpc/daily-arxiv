"""Reusable output templates and field standards for multi-source documents."""

from __future__ import annotations

from typing import Any, Dict, List

from src.models.document_schema import DocumentSchema, SCHEMA_VERSION


OUTPUT_JSON_SCHEMA_VERSION = SCHEMA_VERSION
READING_SUGGESTION_FIELDS = [
    "why_relevant",
    "read_priority",
    "recommended_action",
    "related_topics",
]

WEB_CARD_FIELDS = [
    "schema_version",
    "source_type",
    "source_name",
    "title",
    "summary",
    "core_viewpoints",
    "research_relevance",
    "worth_reading",
    "follow_up_suggestions",
    "description",
    "authors_or_orgs",
    "author_line",
    "published_at",
    "badges",
    "links",
    "reading_suggestion",
    "source_metadata",
]

COMMON_FRONTMATTER_FIELDS = [
    "schema_version",
    "source_type",
    "source_name",
    "title",
    "published_at",
    "collected_at",
    "url",
    "tags",
    "entities",
    "research_direction",
    "importance_score",
]

SOURCE_FRONTMATTER_FIELDS = {
    "paper": ["arxiv_id", "doi", "categories"],
    "policy": ["issuing_body", "policy_level", "region", "effective_date"],
    "news": ["media_name", "region", "event_type"],
    "industry_report": ["institution", "report_type", "region"],
}

MARKDOWN_TEMPLATES = {
    "paper": """# {title}\n\n## 摘要\n{summary}\n\n## 核心元数据\n- 作者/机构: {authors_or_orgs}\n- 类别: {categories}\n- 链接: {url}\n\n## 阅读建议\n- 相关性: {why_relevant}\n- 优先级: {read_priority}\n- 建议动作: {recommended_action}\n- 相关主题: {related_topics}\n""",
    "policy": """# {title}\n\n## 政策概述\n{summary}\n\n## 核心元数据\n- 发布机构: {issuing_body}\n- 政策层级: {policy_level}\n- 地区: {region}\n- 生效日期: {effective_date}\n- 链接: {url}\n\n## 阅读建议\n- 相关性: {why_relevant}\n- 优先级: {read_priority}\n- 建议动作: {recommended_action}\n- 相关主题: {related_topics}\n""",
    "news": """# {title}\n\n## 新闻速览\n{summary}\n\n## 核心元数据\n- 媒体: {media_name}\n- 地区: {region}\n- 事件类型: {event_type}\n- 链接: {url}\n\n## 阅读建议\n- 相关性: {why_relevant}\n- 优先级: {read_priority}\n- 建议动作: {recommended_action}\n- 相关主题: {related_topics}\n""",
    "industry_report": """# {title}\n\n## 行业报告概览\n{summary}\n\n## 核心元数据\n- 发布机构: {institution}\n- 报告类型: {report_type}\n- 地区: {region}\n- 链接: {url}\n\n## 阅读建议\n- 相关性: {why_relevant}\n- 优先级: {read_priority}\n- 建议动作: {recommended_action}\n- 相关主题: {related_topics}\n""",
}


def build_frontmatter(document: DocumentSchema | Dict[str, Any]) -> Dict[str, Any]:
    """Build normalized YAML frontmatter fields for a document."""
    payload = _to_payload(document)
    source_type = payload["source_type"]

    frontmatter: Dict[str, Any] = {}
    for field_name in COMMON_FRONTMATTER_FIELDS + SOURCE_FRONTMATTER_FIELDS.get(source_type, []):
        value = payload.get(field_name)
        if value in (None, "", [], {}):
            continue
        frontmatter[field_name] = value

    frontmatter["reading_suggestion"] = {
        key: payload["reading_suggestion"].get(key)
        for key in READING_SUGGESTION_FIELDS
        if payload["reading_suggestion"].get(key) not in (None, "", [], {})
    }
    return frontmatter


def render_markdown_card(document: DocumentSchema | Dict[str, Any]) -> str:
    """Render a normalized document into a Markdown card with frontmatter."""
    payload = _to_payload(document)
    template = MARKDOWN_TEMPLATES[payload["source_type"]]
    frontmatter = build_frontmatter(payload)
    body = template.format(**_template_context(payload))
    return _render_frontmatter(frontmatter) + "\n" + body.strip() + "\n"


def build_web_card_payload(
    document: DocumentSchema | Dict[str, Any],
    raw_record: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a stable web-facing card payload from canonical document fields."""
    payload = _to_payload(document)
    raw_record = raw_record or {}
    suggestion = payload.get("reading_suggestion", {})
    authors = payload.get("authors_or_orgs", [])
    badges = _merge_badges(payload.get("categories", []), payload.get("tags", []))

    primary_url = raw_record.get("entry_url") or payload.get("url") or raw_record.get("pdf_url") or ""
    pdf_url = raw_record.get("pdf_url") or payload.get("url") or primary_url
    source_url = raw_record.get("entry_url") or payload.get("url") or ""
    description = payload.get("summary") or payload.get("raw_text") or ""

    source_metadata = {
        key: value
        for key, value in {
            "arxiv_id": payload.get("arxiv_id"),
            "doi": payload.get("doi"),
            "categories": payload.get("categories", []),
            "issuing_body": payload.get("issuing_body"),
            "policy_level": payload.get("policy_level"),
            "region": payload.get("region"),
            "effective_date": payload.get("effective_date"),
            "media_name": payload.get("media_name"),
            "event_type": payload.get("event_type"),
            "institution": payload.get("institution"),
            "report_type": payload.get("report_type"),
            "citation_count": raw_record.get("citation_count"),
            "openalex_primary_topic": raw_record.get("openalex_primary_topic"),
            "openalex_topics": raw_record.get("openalex_topics", []),
            "openalex_concepts": raw_record.get("openalex_concepts", []),
            "openalex_institutions": raw_record.get("openalex_institutions", []),
            "openalex_referenced_works_count": raw_record.get("openalex_referenced_works_count"),
            "openalex_updated_date": raw_record.get("openalex_updated_date"),
            "impact_bracket": raw_record.get("impact_bracket", ""),
        }.items()
        if value not in (None, "", [], {})
    }

    return {
        "schema_version": payload.get("schema_version", OUTPUT_JSON_SCHEMA_VERSION),
        "source_type": payload.get("source_type", "paper"),
        "source_name": payload.get("source_name", ""),
        "title": payload.get("title", ""),
        "summary": payload.get("summary", ""),
        "core_viewpoints": payload.get("core_viewpoints", []),
        "research_relevance": payload.get("research_relevance", ""),
        "worth_reading": payload.get("worth_reading"),
        "follow_up_suggestions": payload.get("follow_up_suggestions", []),
        "description": description,
        "authors_or_orgs": authors,
        "author_line": _build_author_line(authors),
        "published_at": payload.get("published_at", ""),
        "badges": badges,
        "links": {
            "primary_url": primary_url,
            "pdf_url": pdf_url,
            "source_url": source_url,
        },
        "reading_suggestion": {
            key: suggestion.get(key, [] if key == "related_topics" else "")
            for key in READING_SUGGESTION_FIELDS
        },
        "source_metadata": source_metadata,
    }


def _template_context(payload: Dict[str, Any]) -> Dict[str, str]:
    suggestion = payload.get("reading_suggestion", {})
    return {
        "title": payload.get("title", ""),
        "summary": payload.get("summary", "暂无摘要"),
        "authors_or_orgs": ", ".join(payload.get("authors_or_orgs", [])) or "暂无",
        "categories": ", ".join(payload.get("categories", [])) or "暂无",
        "url": payload.get("url", ""),
        "issuing_body": payload.get("issuing_body") or "暂无",
        "policy_level": payload.get("policy_level") or "暂无",
        "region": payload.get("region") or "暂无",
        "effective_date": payload.get("effective_date") or "暂无",
        "media_name": payload.get("media_name") or "暂无",
        "event_type": payload.get("event_type") or "暂无",
        "institution": payload.get("institution") or "暂无",
        "report_type": payload.get("report_type") or "暂无",
        "why_relevant": suggestion.get("why_relevant", "暂无"),
        "read_priority": suggestion.get("read_priority", "medium"),
        "recommended_action": suggestion.get("recommended_action", "review"),
        "related_topics": ", ".join(suggestion.get("related_topics", [])) or "暂无",
    }


def _to_payload(document: DocumentSchema | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(document, DocumentSchema):
        return document.to_dict()
    return dict(document)


def _build_author_line(authors: List[str]) -> str:
    if not authors:
        return ""
    preview = authors[:3]
    suffix = " et al." if len(authors) > 3 else ""
    return ", ".join(preview) + suffix


def _merge_badges(categories: List[str], tags: List[str]) -> List[str]:
    merged: List[str] = []
    for item in [*(categories or []), *(tags or [])]:
        if item and item not in merged:
            merged.append(item)
    return merged


def _render_frontmatter(frontmatter: Dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.extend(_render_frontmatter_value(key, value))
    lines.append("---")
    return "\n".join(lines)


def _render_frontmatter_value(key: str, value: Any) -> List[str]:
    if isinstance(value, dict):
        lines = [f"{key}:"]
        for nested_key, nested_value in value.items():
            lines.extend(_render_frontmatter_value(f"  {nested_key}", nested_value))
        return lines

    if isinstance(value, list):
        lines = [f"{key}:"]
        for item in value:
            lines.append(f"  - {item}")
        return lines

    return [f"{key}: {value}"]
