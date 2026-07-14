"""Structured LLM summarization for every supported document source."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from src.exporters.output_templates import build_web_card_payload
from src.sources.structured_metadata import parse_json_object, string_list, unique
from src.utils import get_data_path, get_date_string, save_json

from .llm_factory import LLMClientFactory


SOURCE_INSTRUCTIONS = {
    "paper": (
        "论文：说明研究问题、方法与数据、主要结果、创新点和局限；"
        "不要把尚未验证的结果写成确定事实。"
    ),
    "policy": (
        "中国政策：识别发布机构、约束或支持力度、适用对象、执行时间、"
        "对国内科研与产业的实际影响。"
    ),
    "news": (
        "新闻：区分已发生事实、相关方表态与推测，说明事件进展、可信证据、"
        "时效性及对国内研究方向的信号价值。"
    ),
    "industry_report": (
        "行业报告：提取机构判断、关键数据、市场或技术进展、趋势依据与潜在偏差，"
        "重点判断对国内产业实践的参考价值。"
    ),
}

SYSTEM_PROMPT = """你是面向中国科研与产业情报工作的文档分析助手。
只能依据输入内容作答，不补造数字、结论或政策条款。最终只返回一个 JSON 对象，
不得使用 Markdown 代码块。JSON 必须使用以下键：
{
  "summary": "150-250字中文概括",
  "core_viewpoints": ["2-5条可独立展示的核心观点"],
  "research_relevance": "与给定研究方向的具体关系；不相关时明确说明",
  "worth_reading": true,
  "follow_up_suggestions": ["1-3条可执行的后续建议"]
}
worth_reading 必须是 JSON 布尔值，其他文字均使用简体中文。"""


class DocumentSummarizer:
    """Generate stable, web-ready summaries for normalized documents."""

    def __init__(self, config: Dict[str, Any], llm_client: Any = None):
        self.config = config
        self.logger = logging.getLogger("daily_arxiv.summarizer")
        self.llm_client = llm_client or LLMClientFactory.create_client(config)
        settings = config.get("summarization", {})
        self.max_input_chars = int(settings.get("max_input_chars", 12000))
        self.max_tokens = int(settings.get("max_tokens", 1400))

    def summarize_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize one canonical or legacy document without mutating the input."""
        prepared = self._prepare_document(document)
        try:
            raw = self.llm_client.generate(
                prompt=self._build_prompt(prepared),
                system_prompt=SYSTEM_PROMPT,
                max_tokens=self.max_tokens,
            )
            result = self._normalize_result(parse_json_object(raw))
            prepared.update(result)
            prepared["summary_error"] = False
        except Exception as exc:
            self.logger.error(
                "文档摘要失败 [%s]: %s", prepared.get("title", "Unknown"), exc
            )
            prepared.update(self._fallback_result(prepared))
            prepared["summary_error"] = True
            prepared["summary_error_message"] = str(exc)

        prepared["summarized_at"] = datetime.now().isoformat()
        prepared["summary_prompt_type"] = prepared["source_type"]
        prepared["web_card"] = build_web_card_payload(prepared, raw_record=document)
        return prepared

    def summarize_documents(
        self,
        documents: List[Dict[str, Any]],
        show_progress: bool = True,
    ) -> List[Dict[str, Any]]:
        """Summarize a mixed-source batch and persist a compatible snapshot."""
        if not documents:
            return []

        iterator = tqdm(documents, desc="摘要文档") if show_progress else documents
        summarized = [self.summarize_document(document) for document in iterator]
        self._save_summaries(summarized)
        return summarized

    def generate_report(self, documents: List[Dict[str, Any]]) -> str:
        """Render a concise mixed-source Markdown report."""
        if not documents:
            return "今日没有可汇总的文档。"

        lines = [
            "# 每日科研情报摘要",
            "",
            f"**日期**: {get_date_string()}",
            f"**文档数量**: {len(documents)}",
            "",
            "---",
        ]
        for index, document in enumerate(documents, 1):
            viewpoints = document.get("core_viewpoints", [])
            lines.extend(
                [
                    "",
                    f"## {index}. {document.get('title', '未命名文档')}",
                    f"- 来源类型: {document.get('source_type', 'paper')}",
                    f"- 来源: {document.get('source_name', '')}",
                    f"- 是否值得阅读: {'是' if document.get('worth_reading') else '否'}",
                    "",
                    document.get("summary", "暂无摘要"),
                ]
            )
            if viewpoints:
                lines.extend(["", "**核心观点**", *[f"- {item}" for item in viewpoints]])
            if document.get("research_relevance"):
                lines.extend(["", f"**研究关系**: {document['research_relevance']}"])
            lines.extend(["", "---"])
        return "\n".join(lines) + "\n"

    def _build_prompt(self, document: Dict[str, Any]) -> str:
        source_type = document["source_type"]
        source_instruction = SOURCE_INSTRUCTIONS[source_type]
        topics = self.config.get("tracking_topics", [])
        topic_text = "、".join(str(topic) for topic in topics) or "未配置"
        profile = self.config.get("research_profile", {})
        profile_focus = "、".join(str(item) for item in profile.get("focus", [])) or "未配置"
        exclusions = "、".join(str(item) for item in profile.get("excluded_directions", [])) or "无"
        organizations = "、".join(document.get("authors_or_orgs", [])) or "未知"
        return (
            f"分析类型：{source_type}\n"
            f"专项要求：{source_instruction}\n"
            f"关注研究方向：{topic_text}\n"
            f"研究边界：{profile_focus}\n"
            f"排除方向：{exclusions}\n"
            f"标题：{document.get('title', '')}\n"
            f"作者或机构：{organizations}\n"
            f"发布日期：{document.get('published_at', '')}\n"
            f"原文或摘要：\n{document.get('raw_text', '')[:self.max_input_chars]}"
        )

    def _prepare_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(document)
        source_type = str(prepared.get("source_type") or "paper").lower()
        if source_type not in SOURCE_INSTRUCTIONS:
            raise ValueError(f"Unsupported source_type: {source_type}")

        prepared["source_type"] = source_type
        prepared.setdefault("source_name", "arXiv" if source_type == "paper" else "")
        prepared.setdefault("authors_or_orgs", list(prepared.get("authors", [])))
        prepared.setdefault(
            "raw_text",
            prepared.get("abstract") or prepared.get("summary") or prepared.get("description") or "",
        )
        return prepared

    @staticmethod
    def _normalize_result(payload: Dict[str, Any]) -> Dict[str, Any]:
        summary = str(payload.get("summary") or payload.get("中文概括") or "").strip()
        viewpoints = unique(
            string_list(payload.get("core_viewpoints") or payload.get("核心观点"))
        )
        relevance = str(
            payload.get("research_relevance") or payload.get("与研究方向关系") or ""
        ).strip()
        suggestions = unique(
            string_list(payload.get("follow_up_suggestions") or payload.get("后续建议"))
        )
        worth_reading = _as_bool(
            payload.get("worth_reading", payload.get("是否值得阅读"))
        )
        if not summary or not viewpoints or not relevance or not suggestions:
            raise ValueError("Structured summary is missing required fields")
        return {
            "summary": summary,
            "core_viewpoints": viewpoints,
            "research_relevance": relevance,
            "worth_reading": worth_reading,
            "follow_up_suggestions": suggestions,
        }

    @staticmethod
    def _fallback_result(document: Dict[str, Any]) -> Dict[str, Any]:
        content = str(document.get("summary") or document.get("raw_text") or "").strip()
        summary = content[:300] if content else "原始内容不足，暂无法生成摘要。"
        return {
            "summary": summary,
            "core_viewpoints": [],
            "research_relevance": "待人工复核",
            "worth_reading": False,
            "follow_up_suggestions": ["检查原文完整性后重新生成摘要"],
        }

    def _save_summaries(self, documents: List[Dict[str, Any]]) -> None:
        data_path = Path(get_data_path(self.config, "summaries"))
        data_path.mkdir(parents=True, exist_ok=True)
        date_string = get_date_string()
        save_json(documents, str(data_path / f"summaries_{date_string}.json"))
        save_json(
            {
                "date": date_string,
                "count": len(documents),
                "documents": documents,
                "papers": documents,
                "summaries": documents,
                "llm_provider": self._provider_name(),
                "llm_model": getattr(self.llm_client, "model", ""),
            },
            str(data_path / "latest.json"),
        )

    def _provider_name(self) -> str:
        getter = getattr(self.llm_client, "get_provider_name", None)
        return str(getter()) if callable(getter) else self.llm_client.__class__.__name__


def _as_bool(value: Optional[Any]) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes", "是", "值得"}:
        return True
    if normalized in {"false", "0", "no", "否", "不值得"}:
        return False
    raise ValueError("worth_reading must be a boolean")
