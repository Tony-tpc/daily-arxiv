"""Export stage for the stage-based daily pipeline."""

from __future__ import annotations

from pathlib import Path

from src.utils import get_date_string

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Write the daily summary report to disk if it was generated."""
    if context.stop_requested or not context.summary_report:
        return context

    context.logger.info(context.text("\n生成每日报告...", "\nGenerating daily report..."))
    report_path = f"data/summaries/report_{get_date_string()}.md"
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as handle:
        handle.write(context.summary_report)

    context.logger.info(context.text(f"📄 每日报告已保存到: {report_path}", f"📄 Daily report saved to: {report_path}"))
    context.artifacts['summary_report'] = report_path
    return context
