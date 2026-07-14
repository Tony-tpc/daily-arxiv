"""Direction-level academic, policy, and industry signal comparison."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import log10
from typing import Any, Dict, Iterable, List


GENERIC_TOPICS = {
    "cn", "中国", "能源", "能源系统", "科研论文", "政策治理", "产业动态",
    "新闻事件", "paper", "policy", "news", "industry_report",
}

JUDGMENTS = {
    "academic_lead": "学术领先但政策/行业弱",
    "policy_driven": "政策驱动增强",
    "industry_attention": "行业高度关注",
    "triple_resonance": "三端共振",
    "emerging": "多源信号培育期",
}


class CrossSourceAnalyzer:
    """Aggregate comparable evidence for each non-generic research direction."""

    def __init__(self, config: Dict[str, Any] | None = None):
        settings = (config or {}).get("analysis", {}).get("cross_source", {})
        self.strong_threshold = float(settings.get("strong_threshold", 60))
        self.resonance_threshold = float(settings.get("resonance_threshold", 55))
        self.weak_threshold = float(settings.get("weak_threshold", 40))
        self.max_representatives = max(1, int(settings.get("max_representatives", 3)))

    def analyze(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return scored directions and an explainable portfolio summary."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for document in documents:
            if not isinstance(document, dict):
                continue
            for topic in set(_topics(document)):
                grouped.setdefault(topic, []).append(document)

        directions = [
            self._analyze_direction(topic, evidence)
            for topic, evidence in grouped.items()
        ]
        directions.sort(
            key=lambda item: (
                -float(item["overall_signal"]),
                -int(item["evidence_counts"]["total"]),
                item["direction"],
            )
        )
        distribution = Counter(item["judgment"] for item in directions)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(documents),
            "direction_count": len(directions),
            "dimensions": ["paper_heat", "policy_support", "industry_attention"],
            "directions": directions,
            "summary": {
                "judgment_distribution": dict(distribution),
                "triple_resonance_directions": [
                    item["direction"]
                    for item in directions
                    if item["judgment_code"] == "triple_resonance"
                ],
                "highest_research_value": _top_direction(directions, "research_value"),
                "highest_application_potential": _top_direction(
                    directions, "application_potential"
                ),
            },
        }

    def _analyze_direction(
        self, topic: str, evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        papers = [item for item in evidence if item.get("source_type") == "paper"]
        policies = [item for item in evidence if item.get("source_type") == "policy"]
        industry = [
            item for item in evidence
            if item.get("source_type") in {"industry_report", "news"}
        ]
        scores = {
            "paper_heat": _aggregate_signal(papers, _paper_signal),
            "policy_support": _aggregate_signal(policies, _policy_signal),
            "industry_attention": _aggregate_signal(industry, _industry_signal),
        }
        code = self._judge(scores, papers, policies, industry)
        research_value = round(
            scores["paper_heat"] * 0.55
            + scores["policy_support"] * 0.25
            + scores["industry_attention"] * 0.20,
            1,
        )
        application_potential = round(
            scores["paper_heat"] * 0.20
            + scores["policy_support"] * 0.35
            + scores["industry_attention"] * 0.45,
            1,
        )
        return {
            "direction": topic,
            "scores": scores,
            "evidence_counts": {
                "paper": len(papers),
                "policy": len(policies),
                "industry_report": sum(
                    item.get("source_type") == "industry_report" for item in industry
                ),
                "news": sum(item.get("source_type") == "news" for item in industry),
                "total": len(evidence),
            },
            "overall_signal": round(sum(scores.values()) / 3, 1),
            "research_value": research_value,
            "application_potential": application_potential,
            "judgment_code": code,
            "judgment": JUDGMENTS[code],
            "rationale": _rationale(code, scores),
            "representative_documents": _representatives(
                evidence, self.max_representatives
            ),
        }

    def _judge(
        self,
        scores: Dict[str, float],
        papers: List[Dict[str, Any]],
        policies: List[Dict[str, Any]],
        industry: List[Dict[str, Any]],
    ) -> str:
        paper = scores["paper_heat"]
        policy = scores["policy_support"]
        industry_score = scores["industry_attention"]
        if papers and policies and industry and min(scores.values()) >= self.resonance_threshold:
            return "triple_resonance"
        if industry and industry_score >= self.strong_threshold and policy < self.resonance_threshold:
            return "industry_attention"
        if policies and policy >= self.strong_threshold and industry_score < self.resonance_threshold:
            return "policy_driven"
        if papers and paper >= self.strong_threshold and policy < self.weak_threshold and industry_score < self.weak_threshold:
            return "academic_lead"
        if policies and policy == max(scores.values()) and policy >= self.resonance_threshold:
            return "policy_driven"
        if industry and industry_score == max(scores.values()) and industry_score >= self.resonance_threshold:
            return "industry_attention"
        return "emerging"


def _topics(document: Dict[str, Any]) -> List[str]:
    values: List[Any] = []
    for field in ("research_direction", "themes", "tags", "topic_directions"):
        raw = document.get(field) or []
        values.extend(raw if isinstance(raw, list) else [raw])
    unique: Dict[str, str] = {}
    for value in values:
        topic = str(value or "").strip()
        key = topic.casefold()
        if topic and key not in GENERIC_TOPICS:
            unique.setdefault(key, topic)
    return list(unique.values())


def _aggregate_signal(documents: List[Dict[str, Any]], scorer) -> float:
    if not documents:
        return 0.0
    average = sum(scorer(document) for document in documents) / len(documents)
    volume_bonus = min(15.0, max(0, len(documents) - 1) * 5.0)
    return round(min(100.0, average + volume_bonus), 1)


def _paper_signal(document: Dict[str, Any]) -> float:
    importance = _score(document, "importance_score", 50.0)
    citations = max(0, int(document.get("citation_count") or 0))
    citation_bonus = min(20.0, log10(citations + 1) * 8.0)
    novelty = _breakdown_score(document, "novelty")
    return min(100.0, importance * 0.75 + novelty * 0.15 + citation_bonus)


def _policy_signal(document: Dict[str, Any]) -> float:
    importance = _score(document, "importance_score", 50.0)
    policy_importance = _breakdown_score(document, "policy_importance")
    strength = {"high": 10.0, "medium": 5.0, "low": 0.0}.get(
        str(document.get("policy_strength") or "").lower(), 0.0
    )
    return min(100.0, max(importance, policy_importance) + strength)


def _industry_signal(document: Dict[str, Any]) -> float:
    importance = _score(document, "importance_score", 50.0)
    if document.get("source_type") == "news":
        return min(100.0, importance * 0.8)
    industry_relevance = _breakdown_score(document, "industry_relevance")
    return min(100.0, max(importance, industry_relevance))


def _score(document: Dict[str, Any], field: str, default: float) -> float:
    raw = document.get(field)
    if raw in (None, ""):
        return default
    try:
        return max(0.0, min(100.0, float(raw)))
    except (TypeError, ValueError):
        return default


def _breakdown_score(document: Dict[str, Any], field: str) -> float:
    breakdown = document.get("ranking_score_breakdown") or {}
    return _score(breakdown, field, 0.0) if isinstance(breakdown, dict) else 0.0


def _representatives(
    documents: Iterable[Dict[str, Any]], limit: int
) -> List[Dict[str, Any]]:
    ordered = sorted(
        documents,
        key=lambda item: (
            -_score(item, "importance_score", 0.0),
            str(item.get("title") or ""),
        ),
    )
    return [
        {
            "id": item.get("id"),
            "source_type": item.get("source_type"),
            "source_name": item.get("source_name"),
            "title": item.get("title"),
            "url": item.get("url"),
            "importance_score": _score(item, "importance_score", 0.0),
        }
        for item in ordered[:limit]
    ]


def _rationale(code: str, scores: Dict[str, float]) -> str:
    prefix = {
        "academic_lead": "论文侧信号显著，政策与产业证据仍不足",
        "policy_driven": "政策支持信号领先，方向进入政策牵引阶段",
        "industry_attention": "行业报告与国内新闻关注显著",
        "triple_resonance": "论文、政策与产业三类证据同时达到强信号",
        "emerging": "已有方向性信号，但跨来源证据尚未形成稳定共振",
    }[code]
    return (
        f"{prefix}；论文热度 {scores['paper_heat']:.1f}，"
        f"政策支持 {scores['policy_support']:.1f}，"
        f"行业关注 {scores['industry_attention']:.1f}。"
    )


def _top_direction(directions: List[Dict[str, Any]], field: str) -> str:
    if not directions:
        return ""
    return max(directions, key=lambda item: float(item[field]))["direction"]
