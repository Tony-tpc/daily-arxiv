"""Fetch stage for the stage-based daily pipeline."""

from __future__ import annotations

import importlib

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Load the primary source adapter and fetch paper records."""
    context.logger.info(context.text("步骤 1: 加载数据来源并抓取论文...", "Step 1: Loading sources and fetching papers..."))
    build_source_registry = importlib.import_module("src.sources.registry").build_source_registry

    context.source_registry = build_source_registry(context.config)
    context.enabled_sources = context.source_registry.get_enabled_sources()
    if not context.enabled_sources:
        raise ValueError(context.text("未找到启用的数据来源", "No enabled data source found"))

    context.primary_source_name = context.enabled_sources[0]
    context.source_adapter = context.source_registry.create(context.primary_source_name)
    context.source_adapter.validate()
    context.source_config = context.source_adapter.source_config

    days_back = context.source_config.get('days_back', 2)
    fallback_days_back = context.source_config.get('fallback_days_back', 7)
    context.papers = context.source_adapter.fetch(days_back=days_back)

    if not context.papers:
        context.logger.warning(context.text(
            f"⚠️  过去{days_back}天没有找到符合条件的论文，尝试扩大到{fallback_days_back}天...",
            f"⚠️  No matching papers found in last {days_back} days, retrying with a {fallback_days_back}-day window..."
        ))
        context.papers = context.source_adapter.fetch(days_back=fallback_days_back)

    if context.papers:
        if hasattr(context.source_adapter, 'print_summary'):
            context.source_adapter.print_summary(context.papers)
    else:
        context.logger.warning(context.text("⚠️  没有找到符合条件的论文", "⚠️  No matching papers found"))
        context.logger.info(context.text("💡 提示: 可以尝试以下方法：", "💡 Tips:"))
        context.logger.info(context.text("   1. 在 config.yaml 中增加 days_back 或 max_results", "   1. Increase days_back or max_results in config.yaml"))
        context.logger.info(context.text("   2. 减少或删除关键词过滤（设置 keywords: []）", "   2. Reduce or remove keyword filters (set keywords: [])"))
        context.logger.info(context.text("   3. 修改类别范围", "   3. Broaden category scope"))
        context.stop_requested = True

    return context
