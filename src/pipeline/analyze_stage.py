"""Trend analysis stage for the stage-based daily pipeline."""

from __future__ import annotations

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Analyze trends using the pipeline context outputs."""
    if context.stop_requested:
        return context

    context.logger.info(context.text("\n步骤 4: 分析研究趋势...", "\nStep 4: Analyzing research trends..."))
    try:
        from src.analyzer.trend_analyzer import TrendAnalyzer
        from src.summarizer.llm_factory import LLMClientFactory

        llm_client = LLMClientFactory.create_client(context.config)
        analyzer = TrendAnalyzer(context.config, llm_client)
        summarized_records = context.summarized_papers or context.normalized_records or context.papers
        input_records = context.normalized_records or context.papers
        context.analysis_result = analyzer.analyze(input_records, summarized_records)
        if context.analysis_result:
            analyzer.print_analysis_summary(context.analysis_result)
    except Exception as exc:
        context.logger.error(context.text(f"趋势分析失败: {str(exc)}", f"Trend analysis failed: {str(exc)}"), exc_info=True)
        context.logger.info(context.text("继续执行后续步骤...", "Continuing with following steps..."))

    return context
