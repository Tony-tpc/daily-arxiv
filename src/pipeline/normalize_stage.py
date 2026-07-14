"""Normalize stage for the stage-based daily pipeline."""

from __future__ import annotations

from typing import Any, Dict, List

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
                canonical = [
                    _canonicalize_record(record, source_name)
                    for record in (normalized or [])
                    if isinstance(record, dict)
                ]
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
            existing = [
                dict(item)
                for item in latest.get('documents', [])
                if isinstance(item, dict)
            ]
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
                existing = [
                    dict(item) for item in fallback_documents if isinstance(item, dict)
                ]
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


def _canonicalize_record(record: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Backfill canonical fields for legacy paper adapters."""
    result = dict(record)
    if result.get('source_type'):
        return result

    if source_name not in {'arxiv', 'openalex_search'}:
        return result

    record_id = str(result.get('id') or result.get('doi') or result.get('entry_url') or '')
    authors = _string_list(result.get('authors'))
    categories = _string_list(result.get('categories'))
    topics = _string_list(result.get('openalex_topics'))
    institutions = _string_list(result.get('openalex_institutions'))
    entry_url = str(result.get('entry_url') or result.get('pdf_url') or '')
    arxiv_id = record_id if source_name == 'arxiv' or 'arxiv.org' in entry_url else None

    result.update({
        'id': record_id,
        'source_type': 'paper',
        'source_name': 'arXiv' if source_name == 'arxiv' else 'OpenAlex',
        'summary': str(result.get('summary') or ''),
        'authors_or_orgs': authors,
        'published_at': str(result.get('published') or ''),
        'collected_at': str(result.get('fetched_at') or ''),
        'url': entry_url,
        'raw_text': str(result.get('abstract') or ''),
        'keywords': _unique(categories + topics),
        'tags': _unique(categories + topics),
        'entities': _unique(authors + institutions),
        'categories': categories,
        'arxiv_id': arxiv_id,
        'doi': result.get('doi') or None,
        'provenance': result.get('provenance') or {
            'collected_via': source_name,
            'source_record_id': record_id,
            'fetch_url': entry_url,
            'metadata': {},
        },
    })
    return result


def _string_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or '').strip()
    return [cleaned] if cleaned else []


def _unique(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
