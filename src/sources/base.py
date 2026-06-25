"""Base abstractions for pluggable source adapters."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseSourceAdapter(ABC):
    """Abstract base class for all source adapters."""

    source_name = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"daily_arxiv.sources.{self.source_name}")

    @property
    @abstractmethod
    def source_config(self) -> Dict[str, Any]:
        """Return source-specific configuration."""

    @abstractmethod
    def fetch(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch raw records from the underlying source."""

    @abstractmethod
    def normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize fetched records into the current in-repo shape."""

    @abstractmethod
    def validate(self) -> None:
        """Validate source-specific configuration and runtime assumptions."""

    @abstractmethod
    def save_raw_snapshot(self, records: List[Dict[str, Any]]) -> None:
        """Persist raw fetched records."""
