"""Compare external research information with the user's topic and routes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Set


DOMAIN_TERMS = (
    "能源系统具身智能", "能源具身智能", "物理能源设备", "多智能体强化学习",
    "深度强化学习", "强化学习", "多智能体", "源网荷储", "虚拟电厂",
    "电力市场", "需求响应", "能源智能体", "数字孪生", "博弈论",
    "机制设计", "自主决策", "自主运行", "协同控制", "智能控制",
    "不确定性", "感知", "决策", "控制", "储能", "微电网",
    "embodied intelligence", "multi-agent reinforcement learning",
    "reinforcement learning", "virtual power plant", "digital twin",
    "game theory", "mechanism design", "demand response", "energy agent",
)

STOP_WORDS = {
    "with", "from", "into", "using", "based", "system", "systems", "energy",
    "research", "method", "model", "topic", "direction", "中的", "面向",
}


class ResearchProfileAnalyzer:
    """Produce explainable profile coverage, gaps, and source-specific follow-ups."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.profile = self.config.get("research_profile", {})
        settings = self.profile.get("comparison", {})
        self.strength_threshold = float(settings.get("strength_threshold", 60))
        self.gap_threshold = float(settings.get("gap_threshold", 30))
        self.follow_up_limit = max(1, int(settings.get("follow_up_per_type", 3)))

    def analyze(
        self,
        documents: List[Dict[str, Any]],
        cross_source_analysis: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Compare configured profile dimensions against current external evidence."""
        dimensions = self._dimensions()
        if not dimensions:
            return self._empty_result("unconfigured")
        usable_documents = [
            item for item in documents
            if isinstance(item, dict) and not self._is_excluded(item)
        ]
        coverage = [
            self._measure_dimension(dimension, usable_documents)
            for dimension in dimensions
        ]
        strengths = [item for item in coverage if item["status"] == "strength"]
        gaps = [item for item in coverage if item["status"] == "gap"]
        reinforcement = self._reinforcement(coverage, cross_source_analysis or {})
        follow_up = self._follow_up(usable_documents, dimensions)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "profile": {
                "topic": str(self.profile.get("topic") or ""),
                "focus": _list(self.profile.get("focus")),
                "technical_routes": _list(self.profile.get("technical_routes")),
                "excluded_directions": _list(self.profile.get("excluded_directions")),
            },
            "coverage": coverage,
            "advantages": strengths,
            "gaps": gaps,
            "reinforcement_directions": reinforcement,
            "follow_up": follow_up,
            "summary": {
                "dimension_count": len(coverage),
                "strength_count": len(strengths),
                "gap_count": len(gaps),
                "average_coverage": round(
                    sum(item["coverage_score"] for item in coverage) / len(coverage), 1
                ),
            },
        }

    def _dimensions(self) -> List[Dict[str, str]]:
        dimensions = []
        topic = str(self.profile.get("topic") or "").strip()
        if topic:
            dimensions.append({"kind": "topic", "name": topic})
        dimensions.extend(
            {"kind": "focus", "name": value}
            for value in _list(self.profile.get("focus"))
        )
        dimensions.extend(
            {"kind": "technical_route", "name": value}
            for value in _list(self.profile.get("technical_routes"))
        )
        seen: Set[str] = set()
        unique_dimensions = []
        for item in dimensions:
            key = item["name"].casefold()
            if key in seen:
                continue
            seen.add(key)
            unique_dimensions.append(item)
        return unique_dimensions

    def _measure_dimension(
        self, dimension: Dict[str, str], documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        target_terms = _terms(dimension["name"])
        evidence = []
        matched_union: Set[str] = set()
        best_ratio = 0.0
        for document in documents:
            matched = target_terms & _document_terms(document)
            if not matched:
                continue
            ratio = len(matched) / max(1, len(target_terms))
            best_ratio = max(best_ratio, ratio)
            matched_union.update(matched)
            evidence.append({
                "id": document.get("id"),
                "source_type": document.get("source_type"),
                "title": document.get("title"),
                "matched_terms": sorted(matched),
                "importance_score": _score(document.get("importance_score")),
            })
        evidence.sort(
            key=lambda item: (-float(item["importance_score"]), str(item.get("title") or ""))
        )
        coverage_score = round(
            min(100.0, best_ratio * 75 + min(25.0, len(evidence) * 5.0)), 1
        )
        if coverage_score >= self.strength_threshold:
            status = "strength"
        elif coverage_score < self.gap_threshold:
            status = "gap"
        else:
            status = "partial"
        return {
            **dimension,
            "coverage_score": coverage_score,
            "status": status,
            "matched_terms": sorted(matched_union),
            "evidence_count": len(evidence),
            "evidence": evidence[:5],
            "explanation": _coverage_explanation(status, coverage_score, len(evidence)),
        }

    def _reinforcement(
        self,
        coverage: List[Dict[str, Any]],
        cross_source_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        result = [
            {
                "direction": item["name"],
                "reason": "研究画像覆盖不足，需要补充方法、数据集或中国能源场景证据。",
                "priority": "high" if item["status"] == "gap" else "medium",
                "coverage_score": item["coverage_score"],
                "origin": "profile_gap",
            }
            for item in sorted(coverage, key=lambda entry: entry["coverage_score"])
            if item["status"] in {"gap", "partial"}
        ]
        profile_terms = set().union(*(_terms(item["name"]) for item in coverage))
        for direction in cross_source_analysis.get("directions", []):
            name = str(direction.get("direction") or "").strip()
            if not name or not (_terms(name) & profile_terms):
                continue
            if any(item["direction"] == name for item in result):
                continue
            result.append({
                "direction": name,
                "reason": f"外部信号判断为“{direction.get('judgment') or '待观察'}”，值得纳入路线验证。",
                "priority": "high" if direction.get("judgment_code") == "triple_resonance" else "medium",
                "coverage_score": 0.0,
                "origin": "external_signal",
            })
        result.sort(key=lambda item: (item["priority"] != "high", item["coverage_score"], item["direction"]))
        return result[:8]

    def _follow_up(
        self,
        documents: List[Dict[str, Any]],
        dimensions: List[Dict[str, str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        profile_terms = set().union(*(_terms(item["name"]) for item in dimensions))
        scored = []
        for document in documents:
            matched = profile_terms & _document_terms(document)
            if not matched:
                continue
            scored.append((
                len(matched) * 20 + _score(document.get("importance_score")),
                document,
                sorted(matched),
            ))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("title") or "")))
        groups = {"papers": [], "policies": [], "industry_cases": []}
        for relevance, document, matched in scored:
            source_type = str(document.get("source_type") or "")
            if source_type == "paper":
                key = "papers"
            elif source_type == "policy":
                key = "policies"
            elif source_type in {"news", "industry_report"}:
                key = "industry_cases"
            else:
                continue
            if len(groups[key]) >= self.follow_up_limit:
                continue
            groups[key].append({
                "id": document.get("id"),
                "source_type": source_type,
                "title": document.get("title"),
                "url": document.get("url") or document.get("entry_url") or "",
                "matched_terms": matched,
                "relevance_score": round(relevance, 1),
                "reason": "与研究画像匹配：" + "、".join(matched[:5]),
            })
        return groups

    def _is_excluded(self, document: Dict[str, Any]) -> bool:
        text = _document_text(document).casefold()
        return any(
            value.casefold() in text
            for value in _list(self.profile.get("excluded_directions"))
        )

    def _empty_result(self, status: str) -> Dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "profile": {},
            "coverage": [],
            "advantages": [],
            "gaps": [],
            "reinforcement_directions": [],
            "follow_up": {"papers": [], "policies": [], "industry_cases": []},
            "summary": {
                "dimension_count": 0,
                "strength_count": 0,
                "gap_count": 0,
                "average_coverage": 0.0,
            },
        }


def _document_text(document: Dict[str, Any]) -> str:
    values: List[Any] = [
        document.get("title"), document.get("raw_text"), document.get("abstract"),
        document.get("description"), document.get("summary"),
    ]
    for field in ("tags", "themes", "research_direction", "keywords", "topic_directions"):
        values.extend(_list(document.get(field)))
    return " ".join(str(value or "") for value in values)


def _document_terms(document: Dict[str, Any]) -> Set[str]:
    return _terms(_document_text(document))


def _terms(value: Any) -> Set[str]:
    text = str(value or "").casefold()
    terms = {term.casefold() for term in DOMAIN_TERMS if term.casefold() in text}
    terms.update(
        token for token in re.findall(r"[a-z][a-z0-9-]{3,}", text)
        if token not in STOP_WORDS
    )
    return terms


def _list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value or 0)))
    except (TypeError, ValueError):
        return 0.0


def _coverage_explanation(status: str, score: float, evidence_count: int) -> str:
    label = {"strength": "已有优势", "partial": "部分覆盖", "gap": "存在差距"}[status]
    return f"{label}：覆盖分 {score:.1f}，找到 {evidence_count} 条外部证据。"
