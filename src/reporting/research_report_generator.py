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

from src.sources.paper_quality import is_high_impact_paper


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
        library_token = ''
        if self.config.get('paper_discovery', {}).get('enabled', False):
            from src.academic_library import PaperLibrary
            library_token = PaperLibrary(self.config).state_token()
            if analysis.get('paper_library_token') != library_token:
                analysis = {}
        filtered = [
            item for item in documents
            if (
                isinstance(item, dict)
                and _in_period(item, start, end)
                and (
                    str(item.get("source_type") or "").lower() != "paper"
                    or is_high_impact_paper(item, self.config)
                )
            )
        ]
        forecast = analysis.get("trend_forecast") or {}
        narratives = analysis.get("narrative_analysis") or {}
        narrative_sections = _narrative_report_sections(narratives)
        sections = (narrative_sections or _legacy_forecast_sections(forecast)) + [
            _document_section(
                "appendix_papers", "来源附录｜论文",
                _ranked(filtered, "paper")[: self.max_items],
            ),
            _document_section(
                "appendix_policies", "来源附录｜中国政策",
                _ranked(filtered, "policy")[: self.max_items],
            ),
            _document_section(
                "appendix_news", "来源附录｜国内新闻",
                _ranked(filtered, "news")[: self.max_items],
            ),
            _document_section(
                "appendix_industry_reports", "来源附录｜行业报告",
                _ranked(filtered, "industry_report")[: self.max_items],
            ),
        ]
        report_id = f"{resolved_type}_{start.isoformat()}_{end.isoformat()}"
        payload = {
            "schema_version": "2.1",
            "paper_library_token": library_token,
            "report_id": report_id,
            "report_type": resolved_type,
            "title": REPORT_TITLES[resolved_type],
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(filtered),
            "source_counts": _source_counts(filtered),
            "forecast_version": forecast.get("schema_version", "legacy"),
            "narrative_version": _narrative_version(narratives),
            "narrative_views": [
                view for view in ("paper", "multi_source") if narratives.get(view)
            ],
            "data_quality": (
                (narratives.get("multi_source") or {}).get("coverage")
                or forecast.get("data_quality", {})
            ),
            "evidence_indexes": {
                view: dict((narratives.get(view) or {}).get("evidence_index") or {})
                for view in ("paper", "multi_source")
                if narratives.get(view)
            },
            "narrative_policy": {
                "mode": "evidence_bound_long_form",
                "requires_evidence_ids": True,
                "unsupported_claim_behavior": "reject_or_disclose_gap",
            },
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
            if section.get("kind") == "narrative":
                narrative = _safe_narrative_markdown(section.get("markdown") or "")
                lines.extend([narrative or "本节暂无可用正文。", ""])
                continue
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
                evidence_ids = [
                    _markdown_text(value) for value in item.get("evidence_ids", [])
                    if str(value).strip()
                ]
                if evidence_ids:
                    lines.append(f"  证据：{', '.join(evidence_ids)}")
                counter_signals = [
                    _markdown_text(value) for value in item.get("counter_signals", [])
                    if str(value).strip()
                ]
                if counter_signals:
                    lines.append(f"  反证条件：{'；'.join(counter_signals)}")
            lines.append("")
        lines.extend(["---", "", "本报告由系统自动生成，重要判断请回查原始来源。", ""])
        return "\n".join(lines)


def _narrative_report_sections(narratives: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reuse the exact successful narratives instead of recreating report conclusions."""
    sections: List[Dict[str, Any]] = []
    labels = {"paper": "论文趋势分析", "multi_source": "四类来源综合分析"}
    for view in ("paper", "multi_source"):
        narrative = narratives.get(view) or {}
        for source_section in narrative.get("sections", []):
            evidence_ids = []
            for claim in source_section.get("claims", []):
                evidence_ids.extend(claim.get("evidence_ids", []))
            sections.append({
                "key": f"narrative_{view}_{source_section.get('id') or 'section'}",
                "kind": "narrative",
                "view": view,
                "title": f"{labels[view]}｜{source_section.get('title') or '正文'}",
                "markdown": str(source_section.get("markdown") or ""),
                "char_count": _visible_length(source_section.get("markdown") or ""),
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "items": [],
            })
        if not narrative:
            continue
        if view == "paper":
            sections.append(_text_section(
                "narrative_paper_opportunities",
                "论文趋势分析｜实验机会矩阵",
                _opportunity_items(narrative.get("opportunities", [])),
            ))
        else:
            sections.append(_text_section(
                "narrative_multi_source_chains",
                "四类来源综合分析｜证据链与可执行实验",
                _evidence_chain_items(narrative.get("evidence_chains", [])),
            ))
    return sections


def _opportunity_items(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        "heading": str(item.get("title") or "实验机会"),
        "body": (
            f"研究问题：{item.get('question') or ''} "
            f"候选方法：{item.get('method') or ''} "
            f"对比基线：{item.get('baseline') or ''} "
            f"验证环境：{item.get('validation') or ''} "
            f"核心指标：{'、'.join(item.get('metrics', []))}"
        ),
        "meta": "证据约束的实验设计",
        "evidence_ids": list(item.get("evidence_ids", [])),
    } for item in opportunities]


def _evidence_chain_items(chains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for chain in chains:
        nodes = []
        for node in chain.get("nodes", []):
            if node.get("status") == "missing":
                nodes.append(f"{node.get('label')}：证据缺口")
            else:
                nodes.append(
                    f"{node.get('label')}：{node.get('summary') or ''}"
                )
        experiment = chain.get("experiment") or {}
        items.append({
            "heading": str(chain.get("topic") or "跨来源研究问题"),
            "body": (
                " → ".join(nodes)
                + f" → 可执行实验：{experiment.get('title') or ''}；"
                f"验证环境：{experiment.get('validation') or ''}"
            ),
            "meta": str(chain.get("causality_note") or "节点对齐不表示因果关系。"),
            "evidence_ids": list(chain.get("evidence_ids", [])),
        })
    return items


def _legacy_forecast_sections(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Keep old artifacts readable while making the downgrade explicit."""
    return [
        _text_section("future_outlook", "兼容视图｜未来趋势总览", _future_outlook(forecast)),
        _text_section(
            "topic_decision_cards", "兼容视图｜主题分析", _topic_decision_cards(forecast)
        ),
        _text_section(
            "cross_source_transmission", "兼容视图｜跨来源传导", _lead_lag_items(forecast)
        ),
        _text_section(
            "near_term_forecast", "兼容视图｜近期预测", _near_term_items(forecast)
        ),
        _text_section(
            "strategic_scenarios", "兼容视图｜战略情景", _scenario_items(forecast)
        ),
        _text_section(
            "research_actions", "兼容视图｜科研行动建议", _research_action_items(forecast)
        ),
        _text_section(
            "monitoring", "兼容视图｜反证与监测清单", _monitoring_items(forecast)
        ),
    ]


def _narrative_version(narratives: Dict[str, Any]) -> str:
    versions = {
        str(item.get("schema_version") or "legacy")
        for item in narratives.values() if isinstance(item, dict)
    }
    return ",".join(sorted(versions)) if versions else "unavailable"


def _visible_length(value: Any) -> int:
    text = re.sub(r"```.*?```", "", str(value or ""), flags=re.DOTALL)
    text = re.sub(r"[`*_>#\[\]()-]", "", text)
    return len(re.sub(r"\s+", "", text))


def _safe_narrative_markdown(value: Any) -> str:
    text = str(value or "").replace("<", "&lt;")
    return re.sub(
        r"\[([^\]]+)\]\((?!https?://)[^)]+\)",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )


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


def _text_section(key: str, title: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"key": key, "title": title, "items": items}


def _future_outlook(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    quality = forecast.get("data_quality") or {}
    forecasts = sorted(
        forecast.get("forecasts", []),
        key=lambda item: (
            {"high": 2, "medium": 1, "low": 0}.get(item.get("confidence"), 0),
            float((item.get("metrics") or {}).get("velocity") or 0),
        ),
        reverse=True,
    )
    quality_body = (
        f"当前有 {quality.get('document_count', 0)} 条事件定期资料，"
        f"覆盖 {quality.get('history_month_count', 0)} 个可用月份。"
        + ("；".join(quality.get("gaps", [])) or "已达到基础历史覆盖要求。")
    ) if forecast else "尚未生成趋势分析 v2；当前仅展示来源附录，不给出未来判断。"
    items = [{
        "heading": "证据覆盖与结论边界",
        "body": quality_body,
        "meta": f"截至 {forecast.get('as_of') or '未知日期'}",
    }]
    for item in forecasts[:3]:
        metrics = item.get("metrics") or {}
        mode = "定量预测" if item.get("mode") == "quantitative" else "低置信情景"
        items.append({
            "heading": f"{item.get('topic')}｜{_trajectory_label(item.get('trajectory'))}",
            "body": (
                f"{mode}；近三个月归一化速度 {float(metrics.get('velocity') or 0):+.3f}，"
                f"最近六个月持续性 {float(metrics.get('persistence') or 0):.0%}。"
                f"驱动依据：{'；'.join(item.get('drivers', []))}"
            ),
            "meta": f"{_confidence_label(item.get('confidence'))} · {len(item.get('evidence_ids', []))} 条代表证据",
            "evidence_ids": item.get("evidence_ids", []),
            "counter_signals": item.get("counter_signals", []),
            "topic_id": item.get("topic_id"),
        })
    return items


def _topic_decision_cards(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for item in forecast.get("forecasts", []):
        metrics = item.get("metrics") or {}
        items.append({
            "heading": str(item.get("topic") or "研究主题"),
            "body": (
                f"方向：{_trajectory_label(item.get('trajectory'))}；"
                f"速度 {float(metrics.get('velocity') or 0):+.3f}；"
                f"加速度 {float(metrics.get('acceleration') or 0):+.3f}；"
                f"持续性 {float(metrics.get('persistence') or 0):.0%}；"
                f"来源多样性 {int(metrics.get('source_diversity') or 0)}。"
                f"科研行动：{item.get('research_action') or ''}"
            ),
            "meta": f"{_confidence_label(item.get('confidence'))} · {item.get('mode')}",
            "evidence_ids": item.get("evidence_ids", []),
            "counter_signals": item.get("counter_signals", []),
            "watch_indicators": item.get("watch_indicators", []),
            "metrics": metrics,
            "topic_id": item.get("topic_id"),
        })
    return items


def _lead_lag_items(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    labels = {
        "paper": "论文", "policy": "政策", "news": "国内新闻",
        "industry_report": "行业报告",
    }
    items = []
    for item in forecast.get("lead_lag", []):
        sequence = " → ".join(
            f"{labels.get(point.get('source_type'), point.get('source_type'))}（{point.get('onset')}）"
            for point in item.get("sequence", [])
        )
        items.append({
            "heading": str(item.get("topic") or "研究主题"),
            "body": sequence or "尚未达到跨来源传导判定门槛。",
            "meta": (
                f"相隔 {item.get('lag_months')} 个月 · {item.get('limitation')}"
                if item.get("status") == "supported"
                else str(item.get("limitation") or "证据不足")
            ),
            "topic_id": item.get("topic_id"),
        })
    return items


def _near_term_items(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for item in forecast.get("forecasts", []):
        projections = item.get("projections", [])
        if projections:
            body = "；".join(
                f"{point.get('months_ahead')}个月后占比 {float(point.get('share') or 0):.1%}"
                f"（80%区间 {float(point.get('lower') or 0):.1%}–{float(point.get('upper') or 0):.1%}）"
                for point in projections
            )
        else:
            body = "未达到定量门槛，仅保留低置信情景。缺口：" + "；".join(
                item.get("data_gaps", [])
            )
        items.append({
            "heading": str(item.get("topic") or "研究主题"),
            "body": body,
            "meta": _confidence_label(item.get("confidence")),
            "evidence_ids": item.get("evidence_ids", []),
            "counter_signals": item.get("counter_signals", []),
            "topic_id": item.get("topic_id"),
        })
    return items


def _scenario_items(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "heading": str(item.get("topic") or "研究主题"),
            "body": (
                f"基准：{item.get('base_case') or ''} "
                f"上行情景：{item.get('upside') or ''} "
                f"下行情景：{item.get('downside') or ''}"
            ),
            "meta": _confidence_label(item.get("confidence")),
            "evidence_ids": item.get("evidence_ids", []),
            "counter_signals": item.get("counter_signals", []),
            "topic_id": item.get("topic_id"),
        }
        for item in forecast.get("scenarios", [])
    ]


def _research_action_items(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "heading": str(item.get("topic") or "研究主题"),
            "body": str(item.get("research_action") or ""),
            "meta": "可执行科研任务",
            "evidence_ids": item.get("evidence_ids", []),
            "topic_id": item.get("topic_id"),
        }
        for item in forecast.get("forecasts", [])
    ]


def _monitoring_items(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "heading": str(item.get("topic") or "研究主题"),
            "body": "监测指标：" + "、".join(item.get("watch_indicators", [])),
            "meta": "达到反证条件时下调趋势判断",
            "counter_signals": item.get("counter_signals", []),
            "topic_id": item.get("topic_id"),
        }
        for item in forecast.get("forecasts", [])
    ]


def _trajectory_label(value: Any) -> str:
    return {"rising": "上升", "declining": "回落", "stable": "稳定"}.get(
        str(value), "不确定"
    )


def _confidence_label(value: Any) -> str:
    return {"high": "高置信", "medium": "中置信", "low": "低置信"}.get(
        str(value), "置信度未知"
    )


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
    return " · ".join(
        item for item in (str(organization), str(published)) if item
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
