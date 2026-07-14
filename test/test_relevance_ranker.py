#!/usr/bin/env python3
"""Tests for explainable mixed-source relevance ranking."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ranking.relevance_ranker import DIMENSIONS, RelevanceRanker


class RelevanceRankerTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tracking_topics": [
                "virtual power plant",
                "reinforcement learning",
                "embodied intelligence for energy systems",
            ],
            "research_profile": {
                "excluded_directions": ["通用机器人操控", "机械臂", "机器人导航", "人形机器人"]
            },
            "ranking": {
                "enabled": True,
                "thresholds": {"high": 70, "medium": 45},
            },
        }
        self.ranker = RelevanceRanker(
            self.config,
            now=datetime(2026, 7, 14, tzinfo=timezone.utc),
        )

    def test_official_domestic_energy_policy_is_high_priority(self):
        result = self.ranker.rank_document(
            {
                "id": "policy-1",
                "source_type": "policy",
                "source_name": "国家能源局",
                "title": "关于虚拟电厂参与需求响应的通知",
                "raw_text": "首次推动虚拟电厂和储能系统参与需求响应。",
                "published_at": "2026-07-01",
                "url": "https://www.nea.gov.cn/example",
                "issuing_body": "国家能源局",
                "policy_strength": "high",
                "policy_level": "national",
                "region": "CN",
            }
        )

        self.assertGreaterEqual(result["importance_score"], 70)
        self.assertEqual(result["reading_suggestion"]["read_priority"], "high")
        self.assertEqual(result["reading_suggestion"]["recommended_action"], "精读")
        self.assertEqual(result["ranking_score_breakdown"]["policy_importance"], 100)
        self.assertEqual(result["ranking_score_breakdown"]["source_credibility"], 100)
        self.assertEqual(set(result["ranking_score_breakdown"]), set(DIMENSIONS))
        self.assertEqual(result["web_card"]["read_priority"], "high")
        self.assertEqual(result["web_card"]["recommended_action"], "精读")

    def test_energy_embodied_paper_outranks_robot_arm_paper(self):
        energy_document = {
            "id": "energy-1",
            "source_type": "paper",
            "source_name": "arXiv",
            "title": "能源系统具身智能与强化学习",
            "raw_text": "能源智能体感知储能系统并控制源网荷储协同。",
            "published_at": "2026-07-10",
        }
        robot_document = {
            "id": "robot-1",
            "source_type": "paper",
            "source_name": "arXiv",
            "title": "具身智能机械臂强化学习",
            "raw_text": "通用机器人操控和机械臂抓取。",
            "published_at": "2026-07-10",
        }

        ranked = self.ranker.rank([robot_document, energy_document])
        energy_result, robot_result = ranked

        self.assertEqual(energy_result["id"], "energy-1")
        self.assertIn("能源系统具身智能", energy_result["research_direction"])
        self.assertEqual(energy_result["reading_suggestion"]["recommended_action"], "精读")
        self.assertEqual(robot_result["reading_suggestion"]["recommended_action"], "存档")
        self.assertEqual(robot_result["ranking_penalties"]["excluded_direction"], -15.0)
        self.assertNotIn("能源系统具身智能", robot_result["research_direction"])

    def test_energy_industry_report_uses_industry_dimension(self):
        result = self.ranker.rank_document(
            {
                "id": "report-1",
                "source_type": "industry_report",
                "source_name": "中国电力科学研究院",
                "title": "虚拟电厂与储能行业进展",
                "raw_text": "报告分析能源系统和源网荷储协同的新型实践。",
                "published_at": "2026-06-20",
                "institution": "中国电力科学研究院",
                "topic_directions": ["虚拟电厂"],
                "trend_assessment": "加速发展",
                "region": "CN",
            }
        )

        self.assertEqual(result["ranking_score_breakdown"]["industry_relevance"], 100)
        self.assertIn("industry_relevance", result["ranking_applicable_dimensions"])
        self.assertNotIn("policy_importance", result["ranking_applicable_dimensions"])
        self.assertIn(result["reading_suggestion"]["read_priority"], {"high", "medium"})

    def test_unrelated_record_still_has_explainable_archive_action(self):
        result = self.ranker.rank_document(
            {
                "id": "news-1",
                "source_type": "news",
                "source_name": "普通来源",
                "title": "无关内容",
            }
        )

        self.assertEqual(result["reading_suggestion"]["read_priority"], "low")
        self.assertEqual(result["reading_suggestion"]["recommended_action"], "存档")
        self.assertIn("未发现明确", result["reading_suggestion"]["why_relevant"])
        self.assertEqual(set(result["ranking_score_breakdown"]), set(DIMENSIONS))
        self.assertIn("importance_score", result["web_card"])


if __name__ == "__main__":
    unittest.main()
