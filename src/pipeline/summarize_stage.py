"""Summarization stage for the stage-based daily pipeline."""

from __future__ import annotations

from src.summarizer.paper_summarizer import PaperSummarizer

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Summarize fetched papers while preserving current fallback behavior."""
    if context.stop_requested:
        return context

    context.logger.info(context.text("\n步骤 2: 总结论文...", "\nStep 2: Summarizing papers..."))
    try:
        summarizer = PaperSummarizer(context.config)
        context.summarized_papers = summarizer.summarize_papers(context.papers)
        context.summary_report = summarizer.generate_daily_report(context.summarized_papers)
        context.artifacts['summary_report'] = f"data/summaries/report_{{date}}.md"
    except Exception as exc:
        context.logger.error(context.text(f"论文总结失败: {str(exc)}", f"Paper summarization failed: {str(exc)}"))
        context.logger.info(context.text("继续执行后续步骤...", "Continuing with following steps..."))
        context.summarized_papers = list(context.papers)
        context.summary_report = ""

    return context
