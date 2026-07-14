"""Golden-file regression tests for stable, Chinese-first exports."""

import unittest
from pathlib import Path

from src.exporters.output_templates import render_markdown_card


GOLDEN_DIR = Path(__file__).parent / "golden"


class ExporterGoldenTests(unittest.TestCase):
    def test_policy_markdown_matches_reviewed_golden_file(self):
        document = {
            "schema_version": "1.0",
            "id": "policy-cn-001",
            "source_type": "policy",
            "source_name": "国家能源局",
            "title": "虚拟电厂参与电力市场政策",
            "published_at": "2026-07-10",
            "collected_at": "2026-07-14T08:00:00Z",
            "url": "https://www.nea.gov.cn/policy-cn-001",
            "tags": ["虚拟电厂", "电力市场"],
            "entities": ["国家能源局"],
            "research_direction": ["能源系统智能化"],
            "importance_score": 92.5,
            "issuing_body": "国家能源局",
            "policy_level": "国家级",
            "region": "CN",
            "effective_date": "2026-08-01",
            "summary": "政策明确支持虚拟电厂参与电力市场。",
            "reading_suggestion": {
                "why_relevant": "直接关联能源智能体参与市场决策。",
                "read_priority": "high",
                "recommended_action": "精读",
                "related_topics": ["需求响应", "源网荷储协同"],
            },
        }

        actual = render_markdown_card(document)
        expected = (GOLDEN_DIR / "policy_card.md").read_text(encoding="utf-8")

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
