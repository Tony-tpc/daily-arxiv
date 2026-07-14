"""Normalize stage for the stage-based daily pipeline."""

from __future__ import annotations

from typing import Any, Dict, List

from src.sources.paper_normalizer import (
    clean_paper_title,
    is_excluded_paper,
    normalize_paper_record,
)
from src.storage.base import build_storage
from src.utils import get_data_path, load_json

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Normalize every fetched source and emit one canonical mixed-source batch."""
    if context.stop_requested:
        return context

    if context.source_adapters and context.source_records:
        context.normalized_by_source = {}
        context.normalized_records = []
        for source_name in context.enabled_sources:
            adapter = context.source_adapters.get(source_name)
            if adapter is None:
                continue
            raw_records = context.source_records.get(source_name, [])
            try:
                normalized = (
                    adapter.normalize(raw_records)
                    if hasattr(adapter, 'normalize')
                    else list(raw_records)
                )
                canonical = []
                for record in normalized or []:
                    if not isinstance(record, dict):
                        continue
                    document = _canonicalize_record(record, source_name, context.config)
                    if document is not None:
                        canonical.append(document)
                context.normalized_by_source[source_name] = canonical
                context.normalized_records.extend(canonical)
                if hasattr(adapter, 'save_enriched_snapshot'):
                    adapter.save_enriched_snapshot(canonical)
                    context.artifacts[f'normalized_snapshot_{source_name}'] = (
                        'data/papers/latest_enriched.json'
                    )
            except Exception as exc:
                context.source_errors[source_name] = str(exc)
                context.logger.exception(context.text(
                    f"来源 {source_name} 规范化失败，继续处理其他来源: {exc}",
                    f"Source {source_name} normalization failed; continuing: {exc}",
                ))
    else:
        if context.source_adapter and hasattr(context.source_adapter, 'normalize'):
            context.normalized_records = context.source_adapter.normalize(context.papers)
        else:
            context.normalized_records = list(context.papers)

        if context.source_adapter and hasattr(context.source_adapter, 'save_enriched_snapshot'):
            context.source_adapter.save_enriched_snapshot(context.normalized_records)
            context.artifacts['normalized_snapshot'] = 'data/papers/latest_enriched.json'

    runtime_config = context.config.get('runtime', {})
    if context.normalized_records and runtime_config.get('merge_with_latest', False):
        try:
            latest = build_storage(context.config).load_latest()
            existing = _normalize_existing_documents(
                latest.get('documents', []), context.config
            )
            baseline_id = str(latest.get('snapshot_id') or 'latest')
            if not existing:
                summaries_path = f"{get_data_path(context.config, 'summaries')}/latest.json"
                summary_payload = load_json(summaries_path) or {}
                fallback_documents = (
                    summary_payload.get('documents')
                    or summary_payload.get('summaries')
                    or summary_payload.get('papers')
                    or []
                )
                existing = _normalize_existing_documents(
                    fallback_documents, context.config
                )
                baseline_id = 'summaries/latest'
            if existing:
                context.normalized_records = existing + context.normalized_records
                context.artifacts['incremental_baseline'] = baseline_id
                context.logger.info(context.text(
                    f"增量任务已合并 {len(existing)} 条现有情报，后续统一去重",
                    f"Incremental job merged {len(existing)} existing documents before deduplication",
                ))
        except Exception as exc:
            context.logger.warning(context.text(
                f"读取增量基线失败，将仅处理本次抓取结果: {exc}",
                f"Could not load the incremental baseline; processing only the new batch: {exc}",
            ))

    if not context.normalized_records:
        context.stop_requested = True
    return context


def _canonicalize_record(
    record: Dict[str, Any],
    source_name: str,
    config: Dict[str, Any],
) -> Dict[str, Any] | None:
    """Backfill canonical fields for legacy paper adapters."""
    if source_name in {'arxiv', 'openalex_search'}:
        return normalize_paper_record(record, source_name, config)
    return dict(record)


def _normalize_existing_documents(
    documents: Any,
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Upgrade legacy papers in an incremental baseline before deduplication."""
    normalized: List[Dict[str, Any]] = []
    for raw in documents if isinstance(documents, list) else []:
        if not isinstance(raw, dict):
            continue
        document = dict(raw)
        source_type = str(document.get('source_type') or '')
        legacy_paper = not source_type and _looks_like_legacy_paper(document)
        if source_type == 'paper' or legacy_paper:
            inferred_source = _infer_paper_source(document)
            upgraded = normalize_paper_record(document, inferred_source, config)
            if upgraded is not None:
                normalized.append(upgraded)
                continue
            if is_excluded_paper(document, config):
                continue
            if source_type == 'paper':
                document['title'] = clean_paper_title(document.get('title'))
                normalized.append(document)
            continue
        normalized.append(document)
    return normalized


def _looks_like_legacy_paper(document: Dict[str, Any]) -> bool:
    return bool(
        {'arxiv_id', 'doi', 'categories', 'openalex_id', 'entry_url'}
        & set(document)
    )


def _infer_paper_source(document: Dict[str, Any]) -> str:
    source_name = str(document.get('source_name') or '').casefold()
    url = str(document.get('url') or document.get('entry_url') or '').casefold()
    if 'arxiv' in source_name or 'arxiv.org' in url or document.get('arxiv_id'):
        return 'arxiv'
    return 'openalex_search'
