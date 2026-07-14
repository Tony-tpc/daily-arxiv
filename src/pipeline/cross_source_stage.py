"""Academic-policy-industry direction comparison stage."""

from __future__ import annotations

from src.analyzer.cross_source_analyzer import CrossSourceAnalyzer

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Analyze the enriched mixed-source records for directional resonance."""
    if context.stop_requested:
        return context
    documents = (
        context.summarized_documents
        or context.summarized_papers
        or context.normalized_records
        or context.papers
    )
    context.cross_source_result = CrossSourceAnalyzer(context.config).analyze(documents)
    context.logger.info(context.text(
        f"跨来源方向分析完成：{context.cross_source_result['direction_count']} 个方向",
        f"Cross-source direction analysis completed: {context.cross_source_result['direction_count']} directions",
    ))
    return context
