"""Knowledge extraction stage for the stage-based daily pipeline."""

from __future__ import annotations

from src.extractor.knowledge_extractor import KnowledgeExtractor

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Run adaptive knowledge extraction with current non-fatal behavior."""
    if context.stop_requested:
        return context

    if context.config.get('knowledge_extraction', {}).get('enabled', True):
        context.logger.info(context.text("\n步骤 3: 自适应结构化知识抽取...", "\nStep 3: Adaptive structured knowledge extraction..."))
        try:
            extractor = KnowledgeExtractor(context.config)
            context.knowledge_result = extractor.extract(context.summarized_papers)
        except Exception as exc:
            context.logger.error(context.text(f"自适应知识抽取失败: {str(exc)}", f"Adaptive knowledge extraction failed: {str(exc)}"), exc_info=True)
            context.logger.info(context.text("继续执行后续步骤...", "Continuing with following steps..."))

    return context
