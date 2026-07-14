"""Explainable mixed-source relevance ranking stage."""

from __future__ import annotations

from src.ranking.relevance_ranker import RelevanceRanker

from .context import PipelineContext


IMPACT_BRACKETS = [(100, "hot"), (25, "high"), (5, "notable")]


def run(context: PipelineContext) -> PipelineContext:
    """Rank normalized documents and retain legacy paper impact brackets."""
    if context.stop_requested or not context.config.get("ranking", {}).get("enabled", True):
        return context

    records = list(context.normalized_records or context.papers)
    ranked = RelevanceRanker(context.config).rank(records)
    for record in ranked:
        citations = int(record.get("citation_count", 0) or 0)
        record["impact_bracket"] = next(
            (label for threshold, label in IMPACT_BRACKETS if citations >= threshold),
            "",
        )
        if isinstance(record.get("web_card"), dict):
            metadata = record["web_card"].setdefault("source_metadata", {})
            if record["impact_bracket"]:
                metadata["impact_bracket"] = record["impact_bracket"]

    context.normalized_records = ranked
    context.logger.info(
        context.text(
            f"科研相关性排序完成: {len(ranked)} 条记录",
            f"Research relevance ranking completed: {len(ranked)} records",
        )
    )
    return context
