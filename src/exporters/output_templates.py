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
