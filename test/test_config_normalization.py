#!/usr/bin/env python3
"""Tests for multi-source config normalization."""

import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import normalize_config


class ConfigNormalizationTests(unittest.TestCase):
    def test_normalize_promotes_legacy_arxiv_into_sources(self):
        config = {
            "arxiv": {
                "categories": ["cs.AI"],
                "days_back": 3,
            }
        }

        normalized = normalize_config(config)

        self.assertIn("sources", normalized)
        self.assertEqual(normalized["sources"]["arxiv"]["categories"], ["cs.AI"])
        self.assertEqual(normalized["arxiv"]["days_back"], 3)

    def test_normalize_adds_outputs_and_analysis_defaults(self):
        normalized = normalize_config({})

        self.assertIn("outputs", normalized)
        self.assertTrue(normalized["outputs"]["markdown"]["enabled"])
        self.assertEqual(normalized["analysis"]["trend_window_days"], [7, 30, 60])

    def test_normalize_backfills_top_level_arxiv_from_sources(self):
        config = {
            "sources": {
                "arxiv": {
                    "enabled": True,
                    "categories": ["cs.LG"],
                }
            }
        }

        normalized = normalize_config(config)

        self.assertEqual(normalized["arxiv"]["categories"], ["cs.LG"])
        self.assertTrue(normalized["sources"]["arxiv"]["enabled"])


if __name__ == "__main__":
    unittest.main()
