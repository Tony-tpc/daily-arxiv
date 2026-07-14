#!/usr/bin/env python3
"""Tests for deterministic multi-source tag and entity extraction."""

import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exporters.output_templates import build_web_card_payload
from src.extractor.tag_extractor import TagExtractor


class TagExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = TagExtractor(
            {
                "tracking_topics": [
                    "virtual power plant",
                    "embodied intelligence for energy systems",
                ],
                "tag_extraction": {"enabled": True},
            }
        )

    def test_extracts_domestic_policy_facets(self):
        result = self.extractor.extract_document(
            {
                "id": "policy-1",
                "source_type": "policy",
                "source_name": "国家能源局",
                "title": "关于虚拟电厂参与需求响应的通知",
                "raw_text": "国家能源局在北京推动虚拟电厂、储能系统参与需求响应。",
                "issuing_body": "国家能源局",
                "region": "CN",
            }
        )

        self.assertIn("虚拟电厂", result["tags"])
        self.assertIn("需求响应", result["tags"])
        self.assertIn("储能系统", result["entities"])
        self.assertIn("北京", result["entities"])
        self.assertIn("中国", result["entities"])
        self.assertIn("国家能源局", result["entities"])
        self.assertIn("能源系统智能化", result["research_direction"])
        self.assertIn("政策治理", result["themes"])
        self.assertEqual(result["tag_facets"]["institutions"], ["国家能源局"])

    def test_extracts_energy_embodied_intelligence_without_robotics(self):
        result = self.extractor.extract_document(
            {
                "id": "paper-1",
                "source_type": "paper",
                "source_name": "arXiv",
                "title": "能源系统中具身智能的强化学习方法",
                "summary": "清华大学研究能源智能体通过传感器感知储能系统并控制源网荷储协同。",
                "authors_or_orgs": ["清华大学"],
            }
        )

        self.assertIn("具身智能", result["tags"])
        self.assertIn("强化学习", result["tags"])
        self.assertIn("能源智能体", result["entities"])
        self.assertIn("传感器", result["entities"])
        self.assertIn("储能系统", result["entities"])
        self.assertIn("清华大学", result["entities"])
        self.assertIn("能源系统具身智能", result["research_direction"])
        self.assertIn("能源具身智能", result["themes"])

    def test_robot_arm_content_is_not_an_energy_embodied_direction(self):
        result = self.extractor.extract_document(
            {
                "source_type": "paper",
                "title": "具身智能机器人机械臂强化学习与导航",
                "summary": "研究人形机器人的机械臂抓取。",
            }
        )

        self.assertIn("具身智能", result["tags"])
        self.assertNotIn("机器人", result["entities"])
        self.assertNotIn("机械臂", result["entities"])
        self.assertNotIn("能源系统具身智能", result["research_direction"])
        self.assertEqual(result["research_direction"], [])

    def test_preserves_existing_values_and_updates_web_card(self):
        result = self.extractor.extract_document(
            {
                "source_type": "news",
                "title": "电力市场中的博弈论",
                "tags": ["人工标注", "博弈论"],
                "entities": ["人工实体"],
                "research_direction": ["人工方向"],
                "web_card": {"badges": ["新闻"]},
            }
        )

        self.assertEqual(result["tags"].count("博弈论"), 1)
        self.assertEqual(result["tags"][0], "人工标注")
        self.assertIn("人工实体", result["web_card"]["entities"])
        self.assertIn("博弈论", result["web_card"]["badges"])
        self.assertIn("能源市场博弈与协同", result["web_card"]["research_direction"])

    def test_web_payload_exposes_filter_fields_directly(self):
        tagged = self.extractor.extract_document(
            {
                "source_type": "industry_report",
                "source_name": "中国电力科学研究院",
                "title": "储能与微电网行业报告",
                "institution": "中国电力科学研究院",
            }
        )
        payload = build_web_card_payload(tagged)

        self.assertEqual(payload["tags"], tagged["tags"])
        self.assertEqual(payload["entities"], tagged["entities"])
        self.assertEqual(payload["themes"], tagged["themes"])
        self.assertEqual(payload["tag_facets"], tagged["tag_facets"])

    def test_disabled_extraction_returns_unchanged_copy(self):
        extractor = TagExtractor({"tag_extraction": {"enabled": False}})
        original = {"title": "虚拟电厂", "tags": ["manual"]}
        self.assertEqual(extractor.extract_document(original), original)
        self.assertIsNot(extractor.extract_document(original), original)


if __name__ == "__main__":
    unittest.main()
