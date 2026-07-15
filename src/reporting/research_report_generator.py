"""Deterministic weekly and stage research-information reports."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote, urlparse


REPORT_TITLES = {
    "weekly": "中国能源具身智能研究信息周报",
    "stage": "中国能源具身智能阶段研究报告",
}


class ResearchReportGenerator:
    """Compose web-ready structured content and portable Markdown/JSON files."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        settings = self.config.get("reporting", {})
        self.output_directory = Path(settings.get("directory", "data/reports"))
        self.max_items = max(1, int(settings.get("max_items_per_section", 6)))
        self.weekly_days = max(1, int(settings.get("weekly_days", 7)))
        self.stage_days = max(1, int(settings.get("stage_days", 180)))

    def generate(
        self,
        documents: List[Dict[str, Any]],
        analysis: Dict[str, Any] | None = None,
        *,
        report_type: str = "weekly",
        period_start: str | date | None = None,
        period_end: str | date | None = None,
    ) -> Dict[str, Any]:
        """Build one report without writing it to disk."""
        resolved_type = str(report_type or "weekly").lower()
        if resolved_type not in REPORT_TITLES:
            raise ValueError("report_type must be weekly or stage")
        end = _as_date(period_end) or date.today()
        default_days = self.weekly_days if resolved_type == "weekly" else self.stage_days
        start = _as_date(period_start) or end - timedelta(days=default_days - 1)
        if start > end:
            raise ValueError("period_start cannot be after period_end")

        analysis = analysis or {}
        filtered = [
            item for item in documents
            if isinstance(item, dict) and _in_period(item, start, end)
        ]
        papers = _ranked(filtered, "paper")[: self.max_items]
        policies = _ranked(filtered, "policy")[: self.max_items]
        industry_news = sorted(
            [
                item for item in filtered
                if item.get("source_type") in {"news", "industry_report"}
            ],
            key=_document_sort_key,
            reverse=True,
        )[: self.max_items]
        sections = [
            _document_section("hot_papers", "热点论文", papers),
            _document_section("policy_guidance", "政策导向", policies),
            _document_section(
                "news_and_industry", "国内新闻与行业报告", industry_news
            ),
            _text_section("key_trends", "关键趋势", _trend_items(analysis)),
            _text_section(
                "research_inspirations", "研究启发", _inspiration_items(analysis)
            ),
            _text_section(
                "next_actions", "后续建议", _recommendation_items(analysis)
            ),
        ]
        report_id = f"{resolved_type}_{start.isoformat()}_{end.isoformat()}"
        payload = {
            "schema_version": "1.0",
            "report_id": report_id,
            "report_type": resolved_type,
            "title": REPORT_TITLES[resolved_type],
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(filtered),
            "source_counts": _source_counts(filtered),
            "sections": sections,
        }
        payload["markdown"] = self.render_markdown(payload)
        return payload

    def save(self, report: Dict[str, Any]) -> Dict[str, str]:
        """Atomically persist an immutable report plus latest pointers."""
        self.output_directory.mkdir(parents=True, exist_ok=True)
        report_id = _safe_filename(report.get("report_id") or "report")
        json_path = self.output_directory / f"{report_id}.json"
        markdown_path = self.output_directory / f"{report_id}.md"
        latest_json = self.output_directory / "latest.json"
        latest_markdown = self.output_directory / "latest.md"
        _atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2))
        _atomic_write(markdown_path, str(report.get("markdown") or ""))
        _atomic_write(latest_json, json.dumps(report, ensure_ascii=False, indent=2))
        _atomic_write(latest_markdown, str(report.get("markdown") or ""))
        return {
            "json": str(json_path),
            "markdown": str(markdown_path),
            "latest_json": str(latest_json),
            "latest_markdown": str(latest_markdown),
        }

    @staticmethod
    def render_markdown(report: Dict[str, Any]) -> str:
        lines = [
            f"# {report.get('title', '')}",
            "",
            f"- 报告周期：{report.get('period_start', '')} 至 {report.get('period_end', '')}",
            f"- 收录文档：{report.get('document_count', 0)} 条",
            f"- 生成时间：{report.get('generated_at', '')}",
            "",
        ]
        for section in report.get("sections", []):
            lines.extend([f"## {section.get('title', '')}", ""])
            items = section.get("items", [])
            if not items:
                lines.extend(["本周期暂无可用证据。", ""])
                continue
            for item in items:
                heading = _markdown_text(item.get("heading") or "未命名条目")
                body = _markdown_text(item.get("body") or "")
                url = _markdown_url(item.get("url"))
                if url:
                    lines.append(f"- [{heading}]({url})")
                else:
                    lines.append(f"- **{heading}**")
                if body:
                    lines.append(f"  {body}")
                meta = _markdown_text(item.get("meta") or "")
                if meta:
                    lines.append(f"  _{meta}_")
            lines.append("")
        lines.extend(["---", "", "本报告由系统自动生成，重要判断请回查原始来源。", ""])
        return "\n".join(lines)


def _document_section(key: str, title: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "items": [
            {
                "heading": str(item.get("title") or "未命名文档"),
                "body": _summary(item),
                "meta": _document_meta(item),
                "url": _safe_url(item.get("url") or item.get("entry_url")),
                "source_type": str(item.get("source_type") or ""),
                "importance_score": _number(item.get("importance_score")),
            }
            for item in documents
        ],
    }


def _text_section(key: str, title: str, items: List[Dict[str, str]]) -> Dict[str, Any]:
    return {"key": key, "title": title, "items": items}


def _trend_items(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    temporal = analysis.get("temporal_trends") or {}
    windows = temporal.get("windows") or {}
    for days in ("7", "30", "60"):
        window = windows.get(days) or {}
        rising = [
            item for item in window.get("topic_momentum", [])
            if item.get("status") in {"new", "rising"}
        ][:3]
        if rising:
            summary = "、".join(
                f"{item.get('name')}（{int(item.get('delta') or 0):+d}）"
                for item in rising
            )
            items.append({
                "heading": f"近 {days} 天上升主题",
                "body": summary,
                "meta": f"当前期 {window.get('current_document_count', 0)} 条证据",
            })
    directions = (analysis.get("cross_source_analysis") or {}).get("directions", [])
    for direction in directions[:3]:
        items.append({
            "heading": str(direction.get("direction") or "跨来源方向"),
            "body": str(direction.get("rationale") or ""),
            "meta": str(direction.get("judgment") or ""),
        })
    return items[:6]


def _inspiration_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    profile = analysis.get("research_profile_analysis") or {}
    profile_items: List[Dict[str, Any]] = []
    for item in profile.get("advantages", [])[:2]:
        profile_items.append({
            "heading": f"已有优势｜{item.get('name') or ''}",
            "body": str(item.get("explanation") or ""),
            "meta": "自身研究画像",
        })
    for item in profile.get("gaps", [])[:2]:
        profile_items.append({
            "heading": f"存在差距｜{item.get('name') or ''}",
            "body": str(item.get("explanation") or ""),
            "meta": "建议补充外部证据",
        })
    for item in profile.get("reinforcement_directions", [])[:2]:
        profile_items.append({
            "heading": f"值得补强｜{item.get('direction') or ''}",
            "body": str(item.get("reason") or ""),
            "meta": f"{item.get('priority') or 'medium'} priority",
        })
    follow_up = profile.get("follow_up") or {}
    for group in ("papers", "policies", "industry_cases"):
        for item in follow_up.get(group, [])[:1]:
            profile_items.append({
                "heading": f"可跟进｜{item.get('title') or ''}",
                "body": str(item.get("reason") or ""),
                "meta": str(item.get("source_type") or ""),
                "url": str(item.get("url") or ""),
                "source_type": str(item.get("source_type") or ""),
            })
    directions = (analysis.get("cross_source_analysis") or {}).get("directions", [])
    templates = {
        "triple_resonance": "优先凝练可验证课题，设计论文方法与中国能源场景的联合验证。",
        "academic_lead": "保持方法领先，同时补查中国政策依据和国内示范案例。",
        "policy_driven": "围绕政策目标拆解可量化科研问题，避免只做政策复述。",
        "industry_attention": "提炼行业痛点与可复现实验设置，验证其是否具备学术增量。",
        "emerging": "继续积累跨来源证据，暂不作高确定性方向判断。",
    }
    cross_source_items = [
        {
            "heading": str(item.get("direction") or "研究方向"),
            "body": templates.get(str(item.get("judgment_code")), templates["emerging"]),
            "meta": str(item.get("judgment") or ""),
        }
        for item in directions[:6]
    ]
    return (profile_items + cross_source_items)[:9]


def _recommendation_items(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    directions = (analysis.get("cross_source_analysis") or {}).get("directions", [])
    recommendations: List[Dict[str, str]] = []
    resonance = [item for item in directions if item.get("judgment_code") == "triple_resonance"]
    if resonance:
        recommendations.append({
            "heading": "优先推进三端共振方向",
            "body": "、".join(str(item.get("direction")) for item in resonance[:3]),
            "meta": "建议进入精读与实验设计",
        })
    reinforcement = (
        analysis.get("research_profile_analysis") or {}
    ).get("reinforcement_directions", [])
    if reinforcement:
        recommendations.append({
            "heading": "按研究画像补强技术路线",
            "body": "、".join(
                str(item.get("direction") or "") for item in reinforcement[:3]
            ),
            "meta": "自身研究对比",
        })
    recommendations.extend([
        {
            "heading": "核验中国政策原文",
            "body": "对报告中的政策结论回查发文机构、发布日期、适用区域与有效状态。",
            "meta": "证据质量",
        },
        {
            "heading": "维护能源具身智能边界",
            "body": "聚焦能源系统中的感知—决策—行动闭环，不扩展为机械臂或通用机器人综述。",
            "meta": "研究聚焦",
        },
        {
            "heading": "补齐跨来源证据",
            "body": "对仅有单一来源的方向，下一周期定向补充论文、政策或中国行业案例。",
            "meta": "下期采集",
        },
    ])
    return recommendations[:6]


def _ranked(documents: List[Dict[str, Any]], source_type: str) -> List[Dict[str, Any]]:
    return sorted(
        [item for item in documents if item.get("source_type") == source_type],
        key=_document_sort_key,
        reverse=True,
    )


def _document_sort_key(document: Dict[str, Any]) -> tuple[float, str]:
    return (
        _number(document.get("importance_score")),
        str(document.get("published_at") or document.get("published") or ""),
    )


def _summary(document: Dict[str, Any]) -> str:
    value = document.get("summary") or document.get("description") or document.get("raw_text") or document.get("abstract") or ""
    if isinstance(value, dict):
        value = value.get("one_sentence_summary") or value.get("summary") or "；".join(
            str(item) for item in value.values() if item
        )
    text = " ".join(str(value).split())
    return text[:280] + ("…" if len(text) > 280 else "")


def _document_meta(document: Dict[str, Any]) -> str:
    organization = document.get("issuing_body") or document.get("media_name") or document.get("institution") or document.get("source_name") or ""
    published = document.get("published_at") or document.get("published") or ""
    score = _number(document.get("importance_score"))
    score_label = f"研究价值 {score:.1f}" if score else ""
    return " · ".join(
        item for item in (str(organization), str(published), score_label) if item
    )


def _source_counts(documents: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in documents:
        source_type = str(item.get("source_type") or "unknown")
        result[source_type] = result.get(source_type, 0) + 1
    return result


def _in_period(document: Dict[str, Any], start: date, end: date) -> bool:
    published = _as_date(
        document.get("published_at")
        or document.get("published")
        or document.get("effective_date")
    )
    return published is None or start <= published <= end


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _number(value: Any) -> float:
    try:
        return round(float(value or 0), 1)
    except (TypeError, ValueError):
        return 0.0


def _safe_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _markdown_text(value: Any) -> str:
    text = escape(str(value or ""))
    return re.sub(r"([\\`*{}\[\]()#+.!_|>])", r"\\\1", text)


def _markdown_url(value: Any) -> str:
    url = _safe_url(value)
    return quote(url, safe=":/?&=%#@+,-._~") if url else ""


def _safe_filename(value: Any) -> str:
    return "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in str(value or "")
    ).strip("_") or "report"


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
