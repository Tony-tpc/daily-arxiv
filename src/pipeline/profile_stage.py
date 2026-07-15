"""User research-profile comparison stage."""

from __future__ import annotations

from src.analyzer.research_profile_analyzer import ResearchProfileAnalyzer

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Compare enriched external information with the configured research profile."""
    if context.stop_requested:
        return context
    documents = (
        context.summarized_documents
        or context.summarized_papers
        or context.normalized_records
        or context.papers
    )
    context.profile_result = ResearchProfileAnalyzer(context.config).analyze(
        documents,
        context.cross_source_result,
    )
    context.logger.info(context.text(
        f"自身研究方向对比完成：{context.profile_result['summary']['dimension_count']} 个维度",
        f"Research profile comparison completed: {context.profile_result['summary']['dimension_count']} dimensions",
    ))
    return context
