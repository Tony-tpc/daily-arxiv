"""Cross-source deduplication and relationship stage."""

from __future__ import annotations

from src.linking.deduplicator import Deduplicator
from src.utils import get_date_string, save_json

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Deduplicate ranked documents and persist their relationship graph."""
    if context.stop_requested or not context.normalized_records:
        return context
    if not context.config.get("linking", {}).get("enabled", True):
        return context

    result = Deduplicator(context.config).process(context.normalized_records)
    context.linking_result = result
    context.normalized_records = result["documents"]

    payload = {
        "date": get_date_string(),
        "count": result["output_count"],
        "documents": result["documents"],
        "linking": {
            key: value for key, value in result.items() if key != "documents"
        },
    }
    save_json(payload, "data/documents/latest.json")
    context.artifacts["linked_documents"] = "data/documents/latest.json"
    context.logger.info(context.text(
        f"跨来源去重完成：移除 {result['duplicates_removed']} 条重复，生成 {result['relation_count']} 组关联",
        f"Cross-source linking removed {result['duplicates_removed']} duplicates and created {result['relation_count']} relations",
    ))
    return context
