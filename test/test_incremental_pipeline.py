"""Tests that source-specific jobs preserve the mixed-source latest view."""

import logging
import unittest
from unittest.mock import Mock, patch

from src.pipeline.context import PipelineContext
from src.pipeline.normalize_stage import run


class IncrementalPipelineTests(unittest.TestCase):
    @patch("src.pipeline.normalize_stage.build_storage")
    def test_normalization_merges_latest_before_linking(self, build_storage):
        build_storage.return_value.load_latest.return_value = {
            "snapshot_id": "baseline-1",
            "documents": [{"id": "paper-1", "source_type": "paper", "title": "Existing"}],
        }
        adapter = Mock()
        adapter.normalize.return_value = [
            {"id": "policy-1", "source_type": "policy", "title": "New policy"}
        ]
        context = PipelineContext(
            config={"runtime": {"merge_with_latest": True}},
            logger=logging.getLogger("test.incremental"),
            text=lambda zh, en: zh,
            enabled_sources=["policy"],
            source_adapters={"policy": adapter},
            source_records={"policy": [{"title": "raw"}]},
        )

        result = run(context)

        self.assertEqual([item["id"] for item in result.normalized_records], ["paper-1", "policy-1"])
        self.assertEqual(result.artifacts["incremental_baseline"], "baseline-1")

    @patch("src.pipeline.normalize_stage.load_json")
    @patch("src.pipeline.normalize_stage.build_storage")
    def test_first_incremental_run_falls_back_to_summary_snapshot(self, build_storage, load_json):
        build_storage.return_value.load_latest.return_value = {}
        load_json.return_value = {
            "documents": [{"id": "paper-legacy", "source_type": "paper"}]
        }
        adapter = Mock()
        adapter.normalize.return_value = [{"id": "news-1", "source_type": "news"}]
        context = PipelineContext(
            config={"runtime": {"merge_with_latest": True}},
            logger=logging.getLogger("test.incremental.fallback"),
            text=lambda zh, en: zh,
            enabled_sources=["rss"],
            source_adapters={"rss": adapter},
            source_records={"rss": [{"title": "raw"}]},
        )

        result = run(context)

        self.assertEqual([item["id"] for item in result.normalized_records], ["paper-legacy", "news-1"])
        self.assertEqual(result.artifacts["incremental_baseline"], "summaries/latest")

    @patch("src.pipeline.normalize_stage.build_storage")
    def test_incremental_baseline_upgrades_legacy_papers_and_excludes_robots(
        self, build_storage
    ):
        build_storage.return_value.load_latest.return_value = {
            "snapshot_id": "legacy-baseline",
            "documents": [
                {
                    "id": "W1",
                    "title": '&lt;span class="word"&gt;Energy Agent Coordination',
                    "categories": ["Energy systems"],
                    "entry_url": "https://openalex.org/W1",
                },
                {
                    "id": "W2",
                    "title": "Power dispatch robots",
                    "categories": ["Energy systems"],
                    "entry_url": "https://openalex.org/W2",
                },
            ],
        }
        adapter = Mock()
        adapter.normalize.return_value = [
            {"id": "policy-1", "source_type": "policy", "title": "New policy"}
        ]
        context = PipelineContext(
            config={
                "runtime": {"merge_with_latest": True},
                "negative_keywords": ["robot"],
            },
            logger=logging.getLogger("test.incremental.legacy"),
            text=lambda zh, en: zh,
            enabled_sources=["policy"],
            source_adapters={"policy": adapter},
            source_records={"policy": [{"title": "raw"}]},
        )

        result = run(context)

        self.assertEqual(
            [item["id"] for item in result.normalized_records],
            ["W1", "policy-1"],
        )
        paper = result.normalized_records[0]
        self.assertEqual(paper["source_type"], "paper")
        self.assertEqual(paper["title"], "Energy Agent Coordination")
        self.assertEqual(paper["schema_version"], "1.0")

    @patch("src.pipeline.normalize_stage.build_storage")
    def test_incremental_baseline_drops_enterprise_news_updates(self, build_storage):
        build_storage.return_value.load_latest.return_value = {
            "snapshot_id": "news-baseline",
            "documents": [
                {
                    "id": "company-update",
                    "source_type": "news",
                    "title": "国家电网有限公司发布新能源发展报告",
                },
                {
                    "id": "grid-news",
                    "source_type": "news",
                    "title": "国家电网否认撤销区域电网",
                },
            ],
        }
        adapter = Mock()
        adapter.normalize.return_value = [
            {"id": "policy-1", "source_type": "policy", "title": "New policy"}
        ]
        context = PipelineContext(
            config={
                "runtime": {"merge_with_latest": True},
                "sources": {"rss": {
                    "exclude_enterprise_updates": True,
                    "enterprise_entity_keywords": ["公司", "集团"],
                    "enterprise_update_keywords": ["发布", "中标"],
                    "enterprise_strong_exclude_keywords": ["上市", "融资"],
                }},
            },
            logger=logging.getLogger("test.incremental.enterprise-news"),
            text=lambda zh, en: zh,
            enabled_sources=["policy"],
            source_adapters={"policy": adapter},
            source_records={"policy": [{"title": "raw"}]},
        )

        result = run(context)

        self.assertEqual(
            [item["id"] for item in result.normalized_records],
            ["grid-news", "policy-1"],
        )


if __name__ == "__main__":
    unittest.main()
