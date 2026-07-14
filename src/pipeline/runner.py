"""Pipeline runner for the stage-based daily workflow."""

from __future__ import annotations

import importlib

from .context import PipelineContext


def run_pipeline(context: PipelineContext) -> PipelineContext:
    """Run the daily workflow through ordered stages."""
    stage_modules = [
        'src.pipeline.fetch_stage',
        'src.pipeline.normalize_stage',
        'src.pipeline.ranking_stage',
        'src.pipeline.linking_stage',
        'src.pipeline.summarize_stage',
        'src.pipeline.export_stage',
        'src.pipeline.extract_stage',
        'src.pipeline.analyze_stage',
    ]

    for module_name in stage_modules:
        stage = importlib.import_module(module_name).run
        context = stage(context)
        if context.stop_requested:
            break

    return context
