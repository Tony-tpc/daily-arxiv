"""Deterministic tags, entities, themes, and research-direction extraction."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping

from src.sources.structured_metadata import unique


TECHNICAL_TOPICS = {
    "虚拟电厂": ["虚拟电厂", "virtual power plant", "vpp"],
    "强化学习": ["强化学习", "reinforcement learning", "deep reinforcement learning"],
    "多智能体系统": ["多智能体", "multi-agent", "multi agent"],
    "博弈论": ["博弈论", "game theory", "stackelberg", "nash"],
    "具身智能": ["具身智能", "embodied intelligence", "embodied ai"],
    "大语言模型": ["大语言模型", "大型语言模型", "large language model", "llm"],
    "数字孪生": ["数字孪生", "digital twin"],
}

APPLICATION_SCENARIOS = {
    "能源管理": ["能源管理", "energy management"],
    "需求响应": ["需求响应", "demand response"],
    "电力市场": ["电力市场", "electricity market", "power market"],
    "微电网": ["微电网", "microgrid"],
    "电力系统调度": ["电力系统调度", "power system dispatch", "economic dispatch"],
    "储能": ["储能", "energy storage", "battery storage"],
    "能源设备自主控制": ["能源设备自主控制", "autonomous energy control"],
    "源网荷储协同": ["源网荷储", "source-grid-load-storage"],
}

ENERGY_ENTITIES = {
    "电网": ["电网", "power grid"],
    "分布式能源": ["分布式能源", "distributed energy resource", "der"],
    "储能系统": ["储能系统", "energy storage system", "ess"],
    "光伏": ["光伏", "photovoltaic", "solar pv"],
    "风电": ["风电", "wind power", "wind farm"],
    "充电桩": ["充电桩", "charging pile", "ev charger"],
    "电动汽车": ["电动汽车", "electric vehicle", "ev"],
    "能源系统": ["能源系统", "energy system"],
    "物理能源设备": ["物理能源设备", "physical energy equipment"],
    "源网荷储": ["源网荷储", "source-grid-load-storage"],
}

EMBODIED_ENTITIES = {
    "能源智能体": ["能源智能体", "energy agent", "autonomous energy agent"],
    "智能控制器": ["智能控制器", "intelligent controller"],
    "传感器": ["传感器", "sensor"],
    "执行器": ["执行器", "actuator"],
    "物理能源设备": ["物理能源设备", "physical energy equipment"],
    "源网荷储": ["源网荷储", "source-grid-load-storage"],
}

DOMESTIC_LOCATIONS = {
    "中国": ["中国", "中华人民共和国", "china", "chinese"],
    "北京": ["北京", "beijing"],
    "上海": ["上海", "shanghai"],
    "天津": ["天津", "tianjin"],
    "重庆": ["重庆", "chongqing"],
    "广东": ["广东", "guangdong"],
    "江苏": ["江苏", "jiangsu"],
    "浙江": ["浙江", "zhejiang"],
    "山东": ["山东", "shandong"],
    "四川": ["四川", "sichuan"],
    "湖北": ["湖北", "hubei"],
    "湖南": ["湖南", "hunan"],
    "河南": ["河南", "henan"],
    "河北": ["河北", "hebei"],
    "安徽": ["安徽", "anhui"],
    "福建": ["福建", "fujian"],
    "陕西": ["陕西", "shaanxi"],
    "香港": ["香港", "hong kong"],
    "澳门": ["澳门", "macao", "macau"],
    "台湾": ["台湾", "taiwan"],
}

KNOWN_INSTITUTIONS = {
    "国家发展改革委": ["国家发展改革委", "国家发改委"],
    "国家能源局": ["国家能源局"],
    "工业和信息化部": ["工业和信息化部", "工信部"],
    "科学技术部": ["科学技术部", "科技部"],
    "教育部": ["教育部"],
    "中国科学院": ["中国科学院", "中科院"],
    "中国工程院": ["中国工程院"],
    "国家自然科学基金委员会": ["国家自然科学基金委员会", "自然科学基金委"],
    "清华大学": ["清华大学", "tsinghua university"],
    "北京大学": ["北京大学", "peking university"],
    "中国电力科学研究院": ["中国电力科学研究院", "中国电科院"],
}

ENERGY_CONTEXT_TERMS = {
    "虚拟电厂",
    "能源管理",
    "需求响应",
    "电力市场",
    "微电网",
    "电力系统调度",
    "储能",
    "能源设备自主控制",
    "源网荷储协同",
    "电网",
    "分布式能源",
    "储能系统",
    "光伏",
    "风电",
    "充电桩",
    "电动汽车",
    "能源系统",
    "物理能源设备",
    "源网荷储",
}

LEARNING_CONTROL_TERMS = {"强化学习", "多智能体系统", "电力系统调度", "智能控制器"}
MARKET_TERMS = {"博弈论", "电力市场"}
EMBODIED_ENERGY_TERMS = {"具身智能", "能源智能体"}
FOUNDATION_MODEL_TERMS = {"大语言模型", "数字孪生", "能源智能体"}

ORGANIZATION_SUFFIXES = (
    "大学",
    "学院",
    "研究院",
    "研究所",
    "委员会",
    "发展改革委",
    "能源局",
    "科学院",
    "实验室",
    "中心",
    "集团",
)


class TagExtractor:
    """Apply explainable local classification before optional LLM enrichment."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        settings = config.get("tag_extraction", {})
        self.enabled = bool(settings.get("enabled", True))
        self.include_configured_topics = bool(settings.get("include_configured_topics", True))
        self.max_tags = int(settings.get("max_tags", 20))
        self.max_entities = int(settings.get("max_entities", 30))

    def extract_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy with explicit fields and grouped facets."""
        result = dict(document)
        if not self.enabled:
            return result
        text = self._document_text(result)
        technical = self._match_aliases(text, TECHNICAL_TOPICS)
        applications = self._match_aliases(text, APPLICATION_SCENARIOS)
        energy_entities = self._match_aliases(text, ENERGY_ENTITIES)
        embodied_entities = self._match_aliases(text, EMBODIED_ENTITIES)
        locations = self._extract_locations(result, text)
        institutions = self._extract_institutions(result, text)

        configured_topics = self._configured_topics(text)
        tags = unique(
            _list_values(result.get("tags")) + technical + applications + configured_topics
        )[: self.max_tags]
        entities = unique(
            _list_values(result.get("entities"))
            + energy_entities
            + embodied_entities
            + locations
            + institutions
        )[: self.max_entities]
        match_values = set(tags + energy_entities + embodied_entities)
        themes = unique(
            _list_values(result.get("themes"))
            + self._derive_themes(match_values)
            + self._source_themes(result.get("source_type"))
        )
        directions = unique(
            _list_values(result.get("research_direction"))
            + self._derive_directions(match_values)
            + configured_topics
        )
        extracted_facets = {
            "technical_topics": technical,
            "application_scenarios": applications,
            "energy_entities": energy_entities,
            "embodied_entities": embodied_entities,
            "locations": locations,
            "institutions": institutions,
        }
        existing_facets = result.get("tag_facets", {})
        if not isinstance(existing_facets, dict):
            existing_facets = {}
        tag_facets = {
            name: unique(_list_values(existing_facets.get(name)) + values)
            for name, values in extracted_facets.items()
        }

        result.update(
            {
                "tags": tags,
                "entities": entities,
                "themes": themes,
                "research_direction": directions,
                "tag_facets": tag_facets,
            }
        )
        if isinstance(result.get("web_card"), dict):
            for field in ("tags", "entities", "themes", "research_direction", "tag_facets"):
                result["web_card"][field] = result[field]
            result["web_card"]["badges"] = unique(
                list(result["web_card"].get("badges", [])) + tags
            )
        return result

    def extract_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.extract_document(document) for document in documents]

    def _configured_topics(self, text: str) -> List[str]:
        if not self.include_configured_topics:
            return []
        topics = [str(topic).strip() for topic in self.config.get("tracking_topics", [])]
        return [topic for topic in topics if topic and _contains(text, topic)]

    @staticmethod
    def _document_text(document: Dict[str, Any]) -> str:
        values: List[str] = []
        for key in ("title", "summary", "raw_text", "abstract", "description"):
            values.append(str(document.get(key) or ""))
        values.extend(_list_values(document.get("core_viewpoints")))
        values.extend(_list_values(document.get("keywords")))
        values.extend(_list_values(document.get("tags")))
        return "\n".join(values).lower()

    @staticmethod
    def _match_aliases(text: str, mapping: Mapping[str, Iterable[str]]) -> List[str]:
        return [
            canonical
            for canonical, aliases in mapping.items()
            if any(_contains(text, alias) for alias in aliases)
        ]

    def _extract_institutions(self, document: Dict[str, Any], text: str) -> List[str]:
        institutions = self._match_aliases(text, KNOWN_INSTITUTIONS)
        semantic_values = [
            document.get("issuing_body"),
            document.get("institution"),
            document.get("media_name"),
        ]
        institutions.extend(str(value).strip() for value in semantic_values if value)
        candidate_values = [
            document.get("source_name"),
            *_list_values(document.get("authors_or_orgs")),
            *_list_values(document.get("openalex_institutions")),
        ]
        for value in candidate_values:
            name = str(value or "").strip()
            if name and (name in institutions or name.endswith(ORGANIZATION_SUFFIXES)):
                institutions.append(name)
        return unique(institutions)

    def _extract_locations(self, document: Dict[str, Any], text: str) -> List[str]:
        locations = self._match_aliases(text, DOMESTIC_LOCATIONS)
        region = str(document.get("region") or "").strip()
        if region.upper() in {"CN", "CHN"}:
            locations.append("中国")
        elif region:
            locations.extend(self._match_aliases(region.lower(), DOMESTIC_LOCATIONS))
        return unique(locations)

    @staticmethod
    def _source_themes(source_type: Any) -> List[str]:
        if source_type == "policy":
            return ["政策治理"]
        if source_type == "industry_report":
            return ["产业发展"]
        return []

    @staticmethod
    def _derive_directions(match_values: set[str]) -> List[str]:
        if not match_values & ENERGY_CONTEXT_TERMS:
            return []
        directions = ["能源系统智能化"]
        if match_values & LEARNING_CONTROL_TERMS:
            directions.append("能源系统强化学习与智能控制")
        if match_values & MARKET_TERMS:
            directions.append("能源市场博弈与协同")
        if match_values & EMBODIED_ENERGY_TERMS:
            directions.append("能源系统具身智能")
        if match_values & FOUNDATION_MODEL_TERMS:
            directions.append("能源基础模型与智能体")
        return directions

    @staticmethod
    def _derive_themes(match_values: set[str]) -> List[str]:
        if not match_values & ENERGY_CONTEXT_TERMS:
            return []
        themes = ["能源系统"]
        if match_values & LEARNING_CONTROL_TERMS:
            themes.append("能源学习与控制")
        if match_values & MARKET_TERMS:
            themes.append("能源市场与协同")
        if match_values & EMBODIED_ENERGY_TERMS:
            themes.append("能源具身智能")
        if match_values & FOUNDATION_MODEL_TERMS:
            themes.append("能源人工智能")
        return themes


def _contains(text: str, alias: str) -> bool:
    term = str(alias).strip().lower()
    if not term:
        return False
    if re.fullmatch(r"[a-z0-9][a-z0-9 .+_-]*", term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def _list_values(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []
