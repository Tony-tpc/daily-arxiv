"""Summarization stage for the stage-based daily pipeline."""

from __future__ import annotations

from src.summarizer.document_summarizer import DocumentSummarizer

# Keep the historical patch/import seam while the pipeline moves to documents.
PaperSummarizer = DocumentSummarizer

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Summarize normalized documents while preserving the legacy result field."""
    if context.stop_requested:
        return context

    context.logger.info(context.text("\n步骤 2: 总结论文...", "\nStep 2: Summarizing papers..."))
    try:
        if context.editorial_processed:
            # Editorial writing already used the shared summarizer and call budget.
            # Persist without constructing another live LLM client or repeating calls.
            summarizer = PaperSummarizer(context.config, llm_client=object())
            context.summarized_documents = list(context.normalized_records)
            context.summarized_papers = context.summarized_documents
            summarizer._save_summaries(context.summarized_documents)
            context.summary_report = summarizer.generate_report(context.summarized_documents)
            if context.config.get('paper_discovery', {}).get('enabled', False):
                from src.academic_library import PaperLibrary
                PaperLibrary(context.config).save_summaries(context.summarized_documents)
            return context
        summarizer = PaperSummarizer(context.config)
        records = context.normalized_records or context.papers
        context.summarized_documents = summarizer.summarize_documents(records)
        context.summarized_papers = context.summarized_documents
        context.summary_report = summarizer.generate_report(context.summarized_documents)
        context.artifacts['summary_report'] = f"data/summaries/report_{{date}}.md"
    except Exception as exc:
        context.logger.error(context.text(f"论文总结失败: {str(exc)}", f"Paper summarization failed: {str(exc)}"))
        context.logger.info(context.text("继续执行后续步骤...", "Continuing with following steps..."))
        context.summarized_documents = list(context.normalized_records or context.papers)
        context.summarized_papers = context.summarized_documents
        context.summary_report = ""

    if context.config.get('paper_discovery', {}).get('enabled', False):
        from src.academic_library import PaperLibrary
        PaperLibrary(context.config).save_summaries(context.summarized_documents)
    return context
