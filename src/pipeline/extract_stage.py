"""Knowledge extraction stage for the stage-based daily pipeline."""

from __future__ import annotations

from src.extractor.knowledge_extractor import KnowledgeExtractor
from src.extractor.tag_extractor import TagExtractor

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Run adaptive knowledge extraction with current non-fatal behavior."""
    if context.stop_requested:
        return context

    records = context.summarized_documents or context.summarized_papers
    tagged_documents = TagExtractor(context.config).extract_documents(records)
    context.summarized_documents = tagged_documents
    context.summarized_papers = tagged_documents
    context.knowledge_result = {
        "documents": tagged_documents,
        "tag_extraction": {"count": len(tagged_documents), "mode": "deterministic"},
    }

    if context.config.get('knowledge_extraction', {}).get('enabled', True):
        context.logger.info(
            context.text(
                "\n步骤 3: 自适应结构化知识抽取...",
                "\nStep 3: Adaptive structured knowledge extraction...",
            )
        )
        try:
            extractor = KnowledgeExtractor(context.config)
            context.knowledge_result = extractor.extract(tagged_documents)
        except Exception as exc:
            context.logger.error(
                context.text(
                    f"自适应知识抽取失败: {str(exc)}",
                    f"Adaptive knowledge extraction failed: {str(exc)}",
                ),
                exc_info=True,
            )
            context.logger.info(
                context.text("继续执行后续步骤...", "Continuing with following steps...")
            )

    return context
