#!/usr/bin/env python3
"""Tests for source adapter registry and arXiv adapter wiring."""

import importlib
import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

arxiv_adapter_module = importlib.import_module("src.sources.arxiv_adapter")
base_module = importlib.import_module("src.sources.base")
registry_module = importlib.import_module("src.sources.registry")

ArxivSourceAdapter = arxiv_adapter_module.ArxivSourceAdapter
BaseSourceAdapter = base_module.BaseSourceAdapter
build_source_registry = registry_module.build_source_registry


class SourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "app": {"language": "zh"},
            "arxiv": {
                "categories": ["cs.AI"],
                "keyword_groups": [],
                "keywords": [],
                "max_results": 5,
                "days_back": 3,
                "fallback_days_back": 7,
            }
        }

    def test_registry_returns_enabled_arxiv_source(self):
        registry = build_source_registry(self.config)

        self.assertEqual(registry.get_enabled_sources(), ["arxiv"])
        adapter = registry.create("arxiv")
        self.assertIsInstance(adapter, BaseSourceAdapter)
        self.assertIsInstance(adapter, ArxivSourceAdapter)

    def test_arxiv_adapter_exposes_legacy_source_config(self):
        adapter = ArxivSourceAdapter(self.config)

        self.assertEqual(adapter.source_config["days_back"], 3)
        adapter.validate()

    def test_arxiv_adapter_normalize_is_passthrough_for_now(self):
        adapter = ArxivSourceAdapter(self.config)
        records = [{"id": "1234.5678", "title": "Example"}]

        self.assertEqual(adapter.normalize(records), records)


if __name__ == "__main__":
    unittest.main()
