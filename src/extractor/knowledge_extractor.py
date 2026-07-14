"""
Adaptive knowledge extractor / 自适应知识抽取器

Extracts generic scientific fields plus topic-adaptive facets from papers.
The feature is domain-agnostic: it induces facets from the configured research
topic instead of hard-coding labels such as RL method or power-market scenario.
"""
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.summarizer.llm_factory import LLMClientFactory
from src.utils import get_date_string, get_language, pick_text, save_json
from src.extractor.tag_extractor import TagExtractor


GENERIC_FIELDS = [
    "problem",
    "method",
    "scenario",
    "assumption",
    "constraint",
    "metric",
    "dataset_or_benchmark",
    "baseline",
    "contribution",
    "limitation",
]


class KnowledgeExtractor:
    """Extract generic fields, adaptive facets, evidence spans, and taxonomy."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.language = get_language(config)
        self.extract_config = config.get("knowledge_extraction", {})
        self.logger = logging.getLogger("daily_arxiv.extractor")
        self.tag_extractor = TagExtractor(config)
        self.llm_client = LLMClientFactory.create_client(config)

    def extract(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run schema induction, per-paper extraction, and taxonomy aggregation."""
        if not papers:
            self.logger.warning(pick_text(self.config, "没有论文可抽取知识", "No papers available for knowledge extraction"))
            return {}

        max_papers = int(self.extract_config.get("max_papers", len(papers)))
        target_papers = self.tag_extractor.extract_documents(papers[:max_papers])
        topic = self._resolve_topic()

        self.logger.info("=" * 60)
        self.logger.info(pick_text(
            self.config,
            f"开始自适应知识抽取: {len(target_papers)} 篇论文",
            f"Starting adaptive knowledge extraction for {len(target_papers)} papers",
        ))
        self.logger.info("=" * 60)

        facet_schema = self.generate_facet_schema(topic, target_papers)
        enriched_papers = []
        for index, paper in enumerate(target_papers, 1):
            self.logger.info(pick_text(
                self.config,
                f"[{index}/{len(target_papers)}] 抽取结构化知识: {paper.get('title', '')[:60]}...",
                f"[{index}/{len(target_papers)}] Extracting structured knowledge: {paper.get('title', '')[:60]}...",
            ))
            enriched_papers.append(self.extract_paper(paper, facet_schema))

        taxonomy = self.build_taxonomy(facet_schema, enriched_papers)
        result = {
            "date": get_date_string(),
            "topic": topic,
            "generic_fields": GENERIC_FIELDS,
            "facet_schema": facet_schema,
            "documents": enriched_papers,
            "papers": enriched_papers,
            "taxonomy": taxonomy,
            "paper_count": len(enriched_papers),
            "llm_provider": self.llm_client.get_provider_name(),
            "llm_model": self.llm_client.model,
            "generated_at": datetime.now().isoformat(),
        }
        self._save_result(result)
        return result

    def generate_facet_schema(self, topic: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate topic-specific facets from config and paper samples."""
        configured = self.extract_config.get("seed_facets", [])
        sample = self._format_paper_samples(papers[:5])
        system_prompt = """You design domain-adaptive scientific-paper extraction schemas.
Return strict JSON only. Do not use markdown.
Facets must be reusable dimensions for comparing papers in the current topic.
Avoid hard-coding one domain unless the topic requires it.
"""
        prompt = f"""Research topic:
{topic}

Universal fields already extracted for every paper:
{json.dumps(GENERIC_FIELDS, ensure_ascii=False)}

Seed facets from configuration, if any:
{json.dumps(configured, ensure_ascii=False)}

Paper samples:
{sample}

Create 4-8 adaptive facets. Return JSON with this shape:
{{
  "facets": [
    {{
      "name": "short_snake_case_name",
      "description": "what this facet captures",
      "examples": ["example value 1", "example value 2"]
    }}
  ]
}}
"""
        try:
            raw = self.llm_client.generate(prompt, system_prompt=system_prompt, max_tokens=1600)
            data = self._parse_json_object(raw)
            facets = data.get("facets", [])
            if isinstance(facets, list) and facets:
                return [self._normalize_facet(facet) for facet in facets if isinstance(facet, dict)]
        except Exception as exc:
            self.logger.warning(pick_text(
                self.config,
                f"自适应 facet schema 生成失败，使用回退 schema: {exc}",
                f"Adaptive facet schema generation failed; using fallback schema: {exc}",
            ))

        return self._fallback_schema()

    def extract_paper(self, paper: Dict[str, Any], facet_schema: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract generic fields and adaptive facet values for one paper."""
        system_prompt = """You extract structured scientific knowledge from paper metadata.
Return strict JSON only. Every non-empty facet value must include an evidence span copied or closely paraphrased from title/abstract/summary.
Use null when information is not available. Keep values concise and canonical.
"""
        prompt = f"""Paper:
Title: {paper.get('title')}
Authors: {', '.join(paper.get('authors', [])[:8])}
Categories: {', '.join(paper.get('categories', []))}
Abstract: {paper.get('abstract')}
Summary: {paper.get('summary', '')}

Generic fields to extract:
{json.dumps(GENERIC_FIELDS, ensure_ascii=False)}

Adaptive facet schema:
{json.dumps(facet_schema, ensure_ascii=False, indent=2)}

Return JSON with this exact shape:
{{
  "generic": {{
    "problem": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "method": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "scenario": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "assumption": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "constraint": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "metric": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "dataset_or_benchmark": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "baseline": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "contribution": {{"value": string|null, "evidence": string|null, "confidence": number}},
    "limitation": {{"value": string|null, "evidence": string|null, "confidence": number}}
  }},
  "adaptive_facets": [
    {{"facet": "facet_name", "value": string|null, "evidence": string|null, "confidence": number}}
  ],
  "new_facets": [
    {{"facet": "new_facet_name", "value": string, "evidence": string, "reason": "why this facet should be added"}}
  ]
}}
"""
        paper_result = paper.copy()
        try:
            raw = self.llm_client.generate(prompt, system_prompt=system_prompt, max_tokens=2600)
            extracted = self._parse_json_object(raw)
            paper_result["knowledge"] = self._normalize_extraction(extracted, facet_schema)
        except Exception as exc:
            self.logger.error(pick_text(
                self.config,
                f"结构化抽取失败 [{paper.get('title', 'Unknown')}]: {exc}",
                f"Structured extraction failed [{paper.get('title', 'Unknown')}]: {exc}",
            ))
            paper_result["knowledge"] = self._fallback_extraction(paper, str(exc))

        paper_result["knowledge_extracted_at"] = datetime.now().isoformat()
        return paper_result

    def build_taxonomy(self, facet_schema: List[Dict[str, Any]], papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate facet values into a dynamic taxonomy."""
        buckets: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        new_facets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for paper in papers:
            title = paper.get("title", "")
            knowledge = paper.get("knowledge", {})
            for item in knowledge.get("adaptive_facets", []):
                facet = item.get("facet")
                value = item.get("value")
                if not facet or not value:
                    continue
                canonical = self._canonicalize(value)
                entry = buckets[facet].setdefault(canonical, {
                    "value": canonical,
                    "count": 0,
                    "papers": [],
                    "evidence_examples": [],
                })
                entry["count"] += 1
                entry["papers"].append(paper.get("id"))
                if item.get("evidence") and len(entry["evidence_examples"]) < 3:
                    entry["evidence_examples"].append({"paper_id": paper.get("id"), "title": title, "evidence": item.get("evidence")})

            for item in knowledge.get("new_facets", []):
                facet = item.get("facet")
                if facet and item.get("value"):
                    new_facets[facet].append({
                        "paper_id": paper.get("id"),
                        "title": title,
                        "value": item.get("value"),
                        "evidence": item.get("evidence"),
                        "reason": item.get("reason"),
                    })

        return {
            "facets": facet_schema,
            "values": {
                facet: sorted(values.values(), key=lambda entry: entry["count"], reverse=True)
                for facet, values in buckets.items()
            },
            "emerging_facets": {
                facet: examples
                for facet, examples in new_facets.items()
                if len(examples) >= int(self.extract_config.get("new_facet_min_support", 2))
            },
        }

    def _save_result(self, result: Dict[str, Any]) -> None:
        data_path = Path("data/knowledge")
        data_path.mkdir(parents=True, exist_ok=True)
        date_str = get_date_string()
        dated_path = data_path / f"knowledge_{date_str}.json"
        latest_path = data_path / "latest.json"
        save_json(result, str(dated_path))
        save_json(result, str(latest_path))
        self.logger.info(pick_text(
            self.config,
            f"💾 自适应知识抽取结果已保存: {latest_path}",
            f"💾 Adaptive knowledge extraction saved: {latest_path}",
        ))

    def _resolve_topic(self) -> str:
        profile = self.config.get("research_profile", {})
        if profile.get("topic"):
            return str(profile["topic"])
        arxiv_config = self.config.get("arxiv", {})
        groups = arxiv_config.get("keyword_groups", [])
        group_text = []
        for group in groups:
            name = group.get("name", "topic")
            terms = ", ".join(group.get("terms", [])[:5])
            group_text.append(f"{name}: {terms}")
        return " | ".join(group_text) if group_text else ", ".join(arxiv_config.get("keywords", []))

    def _format_paper_samples(self, papers: List[Dict[str, Any]]) -> str:
        lines = []
        for paper in papers:
            lines.append(f"- Title: {paper.get('title')}\n  Abstract: {paper.get('abstract', '')[:900]}")
        return "\n".join(lines)

    def _parse_json_object(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1)
        else:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)

    def _normalize_facet(self, facet: Dict[str, Any]) -> Dict[str, Any]:
        name = re.sub(r"[^a-zA-Z0-9]+", "_", str(facet.get("name", "facet")).strip().lower()).strip("_")
        return {
            "name": name or "facet",
            "description": str(facet.get("description", "")),
            "examples": [str(item) for item in facet.get("examples", []) if item],
        }

    def _normalize_extraction(self, extracted: Dict[str, Any], facet_schema: List[Dict[str, Any]]) -> Dict[str, Any]:
        generic = extracted.get("generic", {}) if isinstance(extracted.get("generic"), dict) else {}
        normalized_generic = {}
        for field in GENERIC_FIELDS:
            item = generic.get(field, {}) if isinstance(generic.get(field), dict) else {"value": generic.get(field)}
            normalized_generic[field] = self._normalize_evidence_item(item)

        known_facets = {facet["name"] for facet in facet_schema}
        adaptive = []
        for item in extracted.get("adaptive_facets", []):
            if not isinstance(item, dict):
                continue
            facet = self._normalize_facet({"name": item.get("facet")}).get("name")
            if facet in known_facets:
                normalized = self._normalize_evidence_item(item)
                normalized["facet"] = facet
                adaptive.append(normalized)

        new_facets = []
        if self.extract_config.get("allow_new_facets", True):
            for item in extracted.get("new_facets", []):
                if isinstance(item, dict) and item.get("facet") and item.get("value"):
                    new_facets.append({
                        "facet": self._normalize_facet({"name": item.get("facet")}).get("name"),
                        "value": str(item.get("value")),
                        "evidence": item.get("evidence"),
                        "reason": item.get("reason"),
                    })

        return {"generic": normalized_generic, "adaptive_facets": adaptive, "new_facets": new_facets}

    def _normalize_evidence_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        confidence = item.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        return {
            "value": item.get("value"),
            "evidence": item.get("evidence"),
            "confidence": max(0.0, min(1.0, confidence)),
        }

    def _canonicalize(self, value: Any) -> str:
        text = str(value).strip()
        aliases = {
            "marl": "multi-agent reinforcement learning",
            "multi agent reinforcement learning": "multi-agent reinforcement learning",
            "multi-agent rl": "multi-agent reinforcement learning",
            "vpp": "virtual power plant",
            "p2p": "peer-to-peer",
        }
        key = re.sub(r"\s+", " ", text.lower().replace("–", "-")).strip()
        return aliases.get(key, text)

    def _fallback_schema(self) -> List[Dict[str, Any]]:
        configured = self.extract_config.get("seed_facets", [])
        if configured:
            return [self._normalize_facet({"name": name, "description": f"Adaptive facet for {name}", "examples": []}) for name in configured]
        return [
            {"name": "method_family", "description": "Main methodological family used by the paper", "examples": []},
            {"name": "application_context", "description": "Domain or application setting", "examples": []},
            {"name": "mechanism_or_process", "description": "Mechanism, process, or interaction model", "examples": []},
            {"name": "constraint_or_risk", "description": "Important constraint, risk, or safety consideration", "examples": []},
            {"name": "evaluation_signal", "description": "Metric, benchmark, or evaluation signal", "examples": []},
        ]

    def _fallback_extraction(self, paper: Dict[str, Any], error: str) -> Dict[str, Any]:
        abstract = paper.get("abstract", "")
        return {
            "generic": {
                field: {"value": None, "evidence": None, "confidence": 0.0}
                for field in GENERIC_FIELDS
            },
            "adaptive_facets": [],
            "new_facets": [],
            "error": error,
            "fallback_evidence": abstract[:300],
        }


def main():
    """Run extraction against existing latest summaries/papers."""
    from src.utils import load_config, load_env, load_json, setup_logging

    load_env()
    config = load_config()
    setup_logging(config)
    summaries_data = load_json("data/summaries/latest.json")
    papers_data = load_json("data/papers/latest.json")
    papers = []
    if summaries_data:
        papers = summaries_data.get("summaries") or summaries_data.get("papers", [])
    if not papers and papers_data:
        papers = papers_data.get("papers", [])
    extractor = KnowledgeExtractor(config)
    extractor.extract(papers)


if __name__ == "__main__":
    main()
