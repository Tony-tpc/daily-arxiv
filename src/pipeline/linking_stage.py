"""Cross-source deduplication and relationship stage."""

from __future__ import annotations

from src.linking.deduplicator import Deduplicator
from src.storage.base import build_storage
from src.utils import get_date_string

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

    snapshot = build_storage(context.config).save_snapshot(
        result["documents"],
        snapshot_date=get_date_string(),
        metadata={
            "stage": "linked",
            "linking": {
                key: value for key, value in result.items() if key != "documents"
            },
        },
    )
    context.artifacts["linked_documents"] = snapshot.location
    context.logger.info(context.text(
        f"跨来源去重完成：移除 {result['duplicates_removed']} 条重复，生成 {result['relation_count']} 组关联",
        f"Cross-source linking removed {result['duplicates_removed']} duplicates and created {result['relation_count']} relations",
    ))
    return context
