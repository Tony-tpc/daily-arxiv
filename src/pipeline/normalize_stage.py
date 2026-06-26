"""Normalize stage for the stage-based daily pipeline."""

from __future__ import annotations

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Normalize source records into the current in-memory shape."""
    if context.stop_requested:
        return context

    if context.source_adapter and hasattr(context.source_adapter, 'normalize'):
        context.normalized_records = context.source_adapter.normalize(context.papers)
    else:
        context.normalized_records = list(context.papers)
    return context
