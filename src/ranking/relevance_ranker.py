"""Explainable relevance ranking for mixed-source research information."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from src.exporters.output_templates import build_web_card_payload
from src.extractor.tag_extractor import TagExtractor
from src.sources.structured_metadata import unique


DIMENSIONS = (
    "topic_relevance",
    "novelty",
    "policy_importance",
    "industry_relevance",
    "source_credibility",
)

DEFAULT_WEIGHTS = {
    "topic_relevance": 0.40,
    "novelty": 0.15,
    "policy_importance": 0.20,
    "industry_relevance": 0.15,
    "source_credibility": 0.10,
}

OFFICIAL_POLICY_INSTITUTIONS = {
    "国家发展改革委",
    "国家能源局",
    "工业和信息化部",
    "科学技术部",
    "教育部",
    "国家自然科学基金委员会",
}

CENTRAL_MEDIA = {"人民网", "人民日报", "新华网", "新华社", "中国新闻网", "央视网"}
INNOVATION_MARKERS = ("创新", "首次", "首个", "新型", "突破", "novel", "first", "new method")


class RelevanceRanker:
    """Score documents, explain results, and emit web-ready reading actions."""

    def __init__(
        self,
        config: Dict[str, Any],
        now: Optional[datetime] = None,
    ):
        self.config = config
        self.settings = config.get("ranking", {})
        configured_weights = self.settings.get("weights", {})
        self.weights = {
            name: float(configured_weights.get(name, DEFAULT_WEIGHTS[name]))
            for name in DIMENSIONS
        }
        thresholds = self.settings.get("thresholds", {})
        self.high_threshold = float(thresholds.get("high", 70))
        self.medium_threshold = float(thresholds.get("medium", 45))
        self.now = _as_utc(now or datetime.now(timezone.utc))
        self.tag_extractor = TagExtractor(config)
        self.excluded_directions = [
            str(value).lower()
            for value in config.get("research_profile", {}).get("excluded_directions", [])
        ]

    def rank(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank copies of all records by research value, then citation count."""
        ranked = [self.rank_document(document) for document in documents]
        ranked.sort(
            key=lambda item: (
                float(item.get("importance_score") or 0),
                int(item.get("citation_count") or 0),
            ),
            reverse=True,
        )
        return ranked

    def rank_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Attach an explainable score and actionable reading suggestion."""
        result = self.tag_extractor.extract_document(document)
        scores = {
            "topic_relevance": self._topic_relevance(result),
            "novelty": self._novelty(result),
            "policy_importance": self._policy_importance(result),
            "industry_relevance": self._industry_relevance(result),
            "source_credibility": self._source_credibility(result),
        }
        applicable = {"topic_relevance", "novelty", "source_credibility"}
        if result.get("source_type") == "policy":
            applicable.add("policy_importance")
        if result.get("source_type") == "industry_report":
            applicable.add("industry_relevance")

        weighted_total = sum(scores[name] * self.weights[name] for name in applicable)
        weight_total = sum(self.weights[name] for name in applicable) or 1.0
        raw_score = weighted_total / weight_total
        penalties = self._penalties(result)
        final_score = round(max(0.0, min(100.0, raw_score + sum(penalties.values()))), 1)
        priority, action = self._reading_action(final_score)
        factors = self._factors(result, scores, applicable)
        related_topics = unique(
            _list_values(result.get("themes"))
            + _list_values(result.get("research_direction"))
            + _list_values(result.get("tags"))
        )[:10]

        result.update(
            {
                "importance_score": final_score,
                "ranking_score_breakdown": {
                    name: round(scores[name], 1) for name in DIMENSIONS
                },
                "ranking_factors": factors,
                "ranking_penalties": penalties,
                "ranking_applicable_dimensions": sorted(applicable),
                "reading_suggestion": {
                    "why_relevant": self._explanation(result, final_score, factors, penalties),
                    "read_priority": priority,
                    "recommended_action": action,
                    "related_topics": related_topics,
                },
            }
        )
        result["web_card"] = build_web_card_payload(result, raw_record=document)
        return result

    @staticmethod
    def _topic_relevance(document: Dict[str, Any]) -> float:
        themes = set(_list_values(document.get("themes")))
        directions = set(_list_values(document.get("research_direction")))
        tags = set(_list_values(document.get("tags")))
        if "能源系统具身智能" in directions:
            return 100.0
        if "能源系统" not in themes and not any("能源" in item for item in directions):
            return 0.0
        score = 55.0
        if "能源系统强化学习与智能控制" in directions:
            score += 25.0
        if "能源市场博弈与协同" in directions:
            score += 20.0
        if "虚拟电厂" in tags:
            score += 15.0
        return min(100.0, score)

    def _novelty(self, document: Dict[str, Any]) -> float:
        published = _parse_datetime(
            document.get("published_at")
            or document.get("published")
            or document.get("effective_date")
        )
        if document.get("source_type") == "paper":
            score = 50.0
        elif published is None:
            score = 35.0
        else:
            age_days = max(0, (self.now - published).days)
            if age_days <= 30:
                score = 80.0
            elif age_days <= 180:
                score = 65.0
            elif age_days <= 365:
                score = 50.0
            else:
                score = 30.0
        text = _document_text(document)
        if any(marker in text for marker in INNOVATION_MARKERS):
            score += 20.0
        return min(100.0, score)

    @staticmethod
    def _policy_importance(document: Dict[str, Any]) -> float:
        if document.get("source_type") != "policy":
            return 0.0
        strength = str(document.get("policy_strength") or "low").lower()
        score = {"high": 80.0, "medium": 60.0, "low": 40.0}.get(strength, 40.0)
        if str(document.get("policy_level") or "").lower() in {"national", "国家级"}:
            score += 10.0
        if str(document.get("region") or "").upper() in {"CN", "CHN", "中国"}:
            score += 5.0
        if str(document.get("issuing_body") or "") in OFFICIAL_POLICY_INSTITUTIONS:
            score += 5.0
        return min(100.0, score)

    @staticmethod
    def _industry_relevance(document: Dict[str, Any]) -> float:
        if document.get("source_type") != "industry_report":
            return 0.0
        score = 45.0
        if "能源系统" in _list_values(document.get("themes")):
            score += 35.0
        if document.get("topic_directions") or document.get("trend_assessment"):
            score += 10.0
        if document.get("institution"):
            score += 10.0
        return min(100.0, score)

    @staticmethod
    def _source_credibility(document: Dict[str, Any]) -> float:
        source_type = str(document.get("source_type") or "")
        source_name = str(document.get("source_name") or "")
        institution = str(
            document.get("issuing_body")
            or document.get("media_name")
            or document.get("institution")
            or ""
        )
        hostname = urlparse(str(document.get("url") or "")).hostname or ""
        if hostname.endswith(".gov.cn") or institution in OFFICIAL_POLICY_INSTITUTIONS:
            return 100.0
        if source_type == "paper" or source_name.lower() in {"arxiv", "openalex"}:
            return 90.0
        if institution in CENTRAL_MEDIA or source_name in CENTRAL_MEDIA:
            return 85.0
        if source_type == "industry_report" and institution:
            return 75.0
        if institution:
            return 65.0
        return 50.0

    def _penalties(self, document: Dict[str, Any]) -> Dict[str, float]:
        text = _document_text(document)
        energy_context = "能源系统" in _list_values(document.get("themes"))
        if not energy_context and any(term in text for term in self.excluded_directions):
            return {"excluded_direction": -15.0}
        return {}

    def _reading_action(self, score: float) -> Tuple[str, str]:
        if score >= self.high_threshold:
            return "high", "精读"
        if score >= self.medium_threshold:
            return "medium", "略读"
        return "low", "存档"

    @staticmethod
    def _factors(
        document: Dict[str, Any],
        scores: Dict[str, float],
        applicable: set[str],
    ) -> List[str]:
        factors: List[str] = []
        directions = _list_values(document.get("research_direction"))
        if directions:
            factors.append("研究方向：" + "、".join(directions[:3]))
        if "policy_importance" in applicable:
            factors.append(f"政策重要性 {scores['policy_importance']:.0f}")
        if "industry_relevance" in applicable:
            factors.append(f"行业相关性 {scores['industry_relevance']:.0f}")
        factors.append(f"来源可信度 {scores['source_credibility']:.0f}")
        factors.append(f"新颖性 {scores['novelty']:.0f}")
        return factors

    @staticmethod
    def _explanation(
        document: Dict[str, Any],
        score: float,
        factors: List[str],
        penalties: Dict[str, float],
    ) -> str:
        if document.get("research_direction"):
            opening = "与能源研究方向存在明确交叉"
        else:
            opening = "未发现明确的能源系统研究交叉信号"
        penalty_text = "；命中排除方向，已降权" if penalties else ""
        return f"{opening}；综合评分 {score:.1f}。" + "；".join(factors) + penalty_text


def _parse_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return _as_utc(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _document_text(document: Dict[str, Any]) -> str:
    values = [
        document.get("title"),
        document.get("summary"),
        document.get("raw_text"),
        document.get("abstract"),
    ]
    return " ".join(str(value or "").lower() for value in values)


def _list_values(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []
