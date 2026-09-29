"""Fetch stage for the stage-based daily pipeline."""

from __future__ import annotations

import importlib

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Fetch every enabled source independently and tolerate partial failures."""
    context.logger.info(context.text("步骤 1: 加载并抓取全部启用来源...", "Step 1: Loading and fetching all enabled sources..."))
    build_source_registry = importlib.import_module("src.sources.registry").build_source_registry

    context.source_registry = build_source_registry(context.config)
    context.enabled_sources = context.source_registry.get_enabled_sources()
    if not context.enabled_sources:
        raise ValueError(context.text("未找到启用的数据来源", "No enabled data source found"))

    context.source_adapters = {}
    context.source_records = {}
    context.source_errors = {}
    context.papers = []

    for source_name in context.enabled_sources:
        try:
            adapter = context.source_registry.create(source_name)
            adapter.validate()
            source_config = adapter.source_config or {}
            context.source_adapters[source_name] = adapter

            if 'days_back' in source_config:
                days_back = source_config.get('days_back', 2)
                records = adapter.fetch(days_back=days_back)
                fallback_days_back = source_config.get('fallback_days_back')
                if not records and fallback_days_back:
                    context.logger.warning(context.text(
                        f"⚠️  {source_name} 在过去{days_back}天无结果，扩大到{fallback_days_back}天重试...",
                        f"⚠️  {source_name} returned no results in {days_back} days; retrying with {fallback_days_back} days...",
                    ))
                    records = adapter.fetch(days_back=fallback_days_back)
            else:
                records = adapter.fetch()

            source_records = [dict(record) for record in (records or [])]
            context.source_records[source_name] = source_records
            coverage = getattr(adapter, 'last_fetch_result', None)
            if coverage is not None and getattr(coverage, 'status', '') in {'partial', 'unavailable'}:
                context.source_errors[source_name] = '; '.join(coverage.errors) or 'pagination_incomplete'
            context.papers.extend(source_records)
            if source_records and hasattr(adapter, 'print_summary'):
                adapter.print_summary(source_records)
            context.logger.info(context.text(
                f"来源 {source_name}: {len(source_records)} 条",
                f"Source {source_name}: {len(source_records)} records",
            ))
        except Exception as exc:
            context.source_errors[source_name] = str(exc)
            context.logger.exception(context.text(
                f"来源 {source_name} 抓取失败，继续处理其他来源: {exc}",
                f"Source {source_name} failed; continuing with remaining sources: {exc}",
            ))

    successful_sources = [name for name in context.enabled_sources if context.source_records.get(name)]
    context.primary_source_name = successful_sources[0] if successful_sources else context.enabled_sources[0]
    context.source_adapter = context.source_adapters.get(context.primary_source_name)
    context.source_config = (
        context.source_adapter.source_config if context.source_adapter is not None else {}
    )

    if not context.papers:
        context.logger.warning(context.text(
            "⚠️  所有启用来源均未返回新记录",
            "⚠️  No enabled source returned new records",
        ))
        context.stop_requested = not context.config.get("paper_discovery", {}).get("enabled", False)

    return context
