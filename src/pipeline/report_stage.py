"""Weekly or stage research-information report generation stage."""

from __future__ import annotations

from src.reporting.research_report_generator import ResearchReportGenerator

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
    generator = ResearchReportGenerator(context.config)
    report_type = context.config.get("reporting", {}).get("default_type", "weekly")
    other_type = 'stage' if report_type == 'weekly' else 'weekly'
    other_report = generator.generate(documents, context.analysis_result, report_type=other_type)
    other_paths = generator.save(other_report)
    context.artifacts[f'{other_type}_report_json'] = other_paths['json']
    context.artifacts[f'{other_type}_report_markdown'] = other_paths['markdown']
    context.report_result = generator.generate(
        documents,
        context.analysis_result,
        report_type=report_type,
    )
    paths = generator.save(context.report_result)
    context.artifacts[f'{report_type}_report_json'] = paths['json']
    context.artifacts[f'{report_type}_report_markdown'] = paths['markdown']
    context.artifacts["research_report_json"] = paths["json"]
    context.artifacts["research_report_markdown"] = paths["markdown"]
    # Preserve legacy artifact keys for existing automation consumers.
    context.artifacts["intelligence_report_json"] = paths["json"]
    context.artifacts["intelligence_report_markdown"] = paths["markdown"]
    context.logger.info(context.text(
        f"研究信息汇总报告已生成：{paths['markdown']}",
        f"Research information report generated: {paths['markdown']}",
    ))
    return context
