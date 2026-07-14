"""Pipeline context objects for the stage-based workflow."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


TextPicker = Callable[[str, str], str]


@dataclass
class PipelineContext:
    """Shared state passed across pipeline stages."""

    config: Dict[str, Any]
    logger: logging.Logger
    text: TextPicker
    source_registry: Any = None
    enabled_sources: List[str] = field(default_factory=list)
    primary_source_name: str = ""
    source_adapter: Any = None
    source_config: Dict[str, Any] = field(default_factory=dict)
    papers: List[Dict[str, Any]] = field(default_factory=list)
    normalized_records: List[Dict[str, Any]] = field(default_factory=list)
    summarized_documents: List[Dict[str, Any]] = field(default_factory=list)
    summarized_papers: List[Dict[str, Any]] = field(default_factory=list)
    summary_report: str = ""
    knowledge_result: Dict[str, Any] = field(default_factory=dict)
    analysis_result: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    stop_requested: bool = False


def create_pipeline_context(config: Dict[str, Any], logger: logging.Logger, text: TextPicker) -> PipelineContext:
    """Create a new pipeline context with standard dependencies."""
    return PipelineContext(config=config, logger=logger, text=text)
