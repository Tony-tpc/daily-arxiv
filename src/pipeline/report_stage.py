"""Weekly or stage intelligence report generation stage."""

from __future__ import annotations

from src.reporting.intelligence_report_generator import IntelligenceReportGenerator

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Generate and persist the configured report from current pipeline results."""
    if context.stop_requested or not context.config.get("reporting", {}).get("enabled", True):
        return context
    documents = (
        context.summarized_documents
        or context.summarized_papers
        or context.normalized_records
        or context.papers
    )
    generator = IntelligenceReportGenerator(context.config)
    report_type = context.config.get("reporting", {}).get("default_type", "weekly")
    context.report_result = generator.generate(
        documents,
        context.analysis_result,
        report_type=report_type,
    )
    paths = generator.save(context.report_result)
    context.artifacts["intelligence_report_json"] = paths["json"]
    context.artifacts["intelligence_report_markdown"] = paths["markdown"]
    context.logger.info(context.text(
        f"研究情报报告已生成：{paths['markdown']}",
        f"Research intelligence report generated: {paths['markdown']}",
    ))
    return context
