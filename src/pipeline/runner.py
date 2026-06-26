"""Pipeline runner for the stage-based daily workflow."""

from __future__ import annotations

from .context import PipelineContext
from . import analyze_stage, export_stage, extract_stage, fetch_stage, normalize_stage, summarize_stage


def run_pipeline(context: PipelineContext) -> PipelineContext:
    """Run the daily workflow through ordered stages."""
    stages = [
        fetch_stage.run,
        normalize_stage.run,
        summarize_stage.run,
        export_stage.run,
        extract_stage.run,
        analyze_stage.run,
    ]

    for stage in stages:
        context = stage(context)
        if context.stop_requested:
            break

    return context
