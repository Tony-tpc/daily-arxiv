#!/usr/bin/env python3
"""Tests for source adapter registry and arXiv adapter wiring."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


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

    def test_arxiv_adapter_delegates_fetch_and_enrichment(self):
        adapter = ArxivSourceAdapter(self.config)
        records = [{"id": "1234.5678", "title": "Example"}]
        adapter.fetcher = Mock()
        adapter.fetcher.fetch_papers.return_value = records
        adapter.openalex_adapter = Mock()
        adapter.openalex_adapter.enrich_records.return_value = [{**records[0], "citation_count": 8}]

        self.assertEqual(adapter.fetch(days_back=2), records)
        normalized = adapter.normalize(records)
        self.assertEqual(normalized[0]["citation_count"], 8)
        self.assertEqual(normalized[0]["source_type"], "paper")
        self.assertEqual(normalized[0]["schema_version"], "1.0")
        self.assertEqual(normalized[0]["arxiv_id"], "1234.5678")
        adapter.fetcher.fetch_papers.assert_called_once_with(days_back=2)
        adapter.openalex_adapter.enrich_records.assert_called_once_with(records)


if __name__ == "__main__":
    unittest.main()
