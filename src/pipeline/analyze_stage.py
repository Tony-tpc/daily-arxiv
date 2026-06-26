"""Trend analysis stage for the stage-based daily pipeline."""

from __future__ import annotations

from src.analyzer.trend_analyzer import TrendAnalyzer
from src.summarizer.llm_factory import LLMClientFactory
from src.utils import load_json

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Analyze trends using persisted summaries, preserving current semantics."""
    if context.stop_requested:
        return context

    context.logger.info(context.text("\n步骤 4: 分析研究趋势...", "\nStep 4: Analyzing research trends..."))
    try:
        llm_client = LLMClientFactory.create_client(context.config)
        summaries_data = load_json('data/summaries/latest.json')
        summaries = summaries_data.get('summaries') or summaries_data.get('papers', []) if summaries_data else []
        analyzer = TrendAnalyzer(context.config, llm_client)
        context.analysis_result = analyzer.analyze(context.papers, summaries)
        if context.analysis_result:
            analyzer.print_analysis_summary(context.analysis_result)
    except Exception as exc:
        context.logger.error(context.text(f"趋势分析失败: {str(exc)}", f"Trend analysis failed: {str(exc)}"), exc_info=True)
        context.logger.info(context.text("继续执行后续步骤...", "Continuing with following steps..."))

    return context
