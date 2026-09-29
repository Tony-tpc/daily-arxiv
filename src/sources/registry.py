"""Registry for pluggable source adapters."""

from __future__ import annotations

from typing import Any, Dict, List, Type

from .arxiv_adapter import ArxivSourceAdapter
from .crossref_adapter import CrossrefAdapter
from .openaire_adapter import OpenAIREAdapter
from .semantic_scholar_adapter import SemanticScholarAdapter
from .base import BaseSourceAdapter
from .industry_report_adapter import IndustryReportSourceAdapter
from .openalex_search_adapter import OpenAlexSearchAdapter
from .policy_adapter import PolicySourceAdapter
from .rss_adapter import RSSSourceAdapter


class SourceRegistry:
    """In-memory registry of available source adapters."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._registry: Dict[str, Type[BaseSourceAdapter]] = {}

    def register(self, name: str, adapter_class: Type[BaseSourceAdapter]) -> None:
        self._registry[name] = adapter_class

    def create(self, name: str) -> BaseSourceAdapter:
        if name not in self._registry:
            raise KeyError(f"Unknown source adapter: {name}")
        return self._registry[name](self.config)

    def list_sources(self) -> List[str]:
        return list(self._registry.keys())

    def get_enabled_sources(self) -> List[str]:
        sources = self.config.get("sources", {}) if isinstance(self.config, dict) else {}
        if isinstance(sources, dict) and sources:
            enabled = []
            for name, source_config in sources.items():
                if not isinstance(source_config, dict):
                    continue
                if source_config.get("enabled", True):
                    enabled.append(name)
            if enabled:
                return [name for name in enabled if name in self._registry]

        return ["arxiv"] if "arxiv" in self._registry and self.config.get("arxiv") else []


def build_source_registry(config: Dict[str, Any]) -> SourceRegistry:
    """Build the default registry for the current repository."""
    registry = SourceRegistry(config)
    registry.register("arxiv", ArxivSourceAdapter)
    registry.register("openalex_search", OpenAlexSearchAdapter)
    registry.register("crossref", CrossrefAdapter)
    registry.register("openaire", OpenAIREAdapter)
    registry.register("semantic_scholar", SemanticScholarAdapter)
    registry.register("rss", RSSSourceAdapter)
    registry.register("policy", PolicySourceAdapter)
    registry.register("industry_report", IndustryReportSourceAdapter)
    return registry
