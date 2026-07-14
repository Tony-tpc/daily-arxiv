#!/usr/bin/env python3
"""Tests for multi-source config normalization."""

import os
import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import load_config, normalize_config


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
        self.assertEqual(normalized["regional_focus"], ["CN"])

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

    def test_normalize_openalex_can_read_env_defaults(self):
        previous_api_key = os.environ.get("OPENALEX_API_KEY")
        previous_email = os.environ.get("OPENALEX_EMAIL")
        os.environ["OPENALEX_API_KEY"] = "env-key"
        os.environ["OPENALEX_EMAIL"] = "env@example.com"
        try:
            normalized = normalize_config({})
            self.assertEqual(normalized["sources"]["openalex"]["api_key"], "env-key")
            self.assertEqual(normalized["sources"]["openalex"]["email"], "env@example.com")
        finally:
            if previous_api_key is None:
                os.environ.pop("OPENALEX_API_KEY", None)
            else:
                os.environ["OPENALEX_API_KEY"] = previous_api_key
            if previous_email is None:
                os.environ.pop("OPENALEX_EMAIL", None)
            else:
                os.environ["OPENALEX_EMAIL"] = previous_email

    def test_repository_content_sources_default_to_china(self):
        config = load_config("config/config.yaml")

        self.assertEqual(config["regional_focus"], ["CN"])
        self.assertTrue(
            all(feed["region"] == "CN" for feed in config["sources"]["rss"]["feeds"])
        )
        self.assertTrue(
            all(feed["region"] == "CN" for feed in config["sources"]["policy"]["feeds"])
        )


if __name__ == "__main__":
    unittest.main()
