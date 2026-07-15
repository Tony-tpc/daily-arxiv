#!/usr/bin/env python3
"""Tests for visual ranking controls and web-card propagation."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web.app import _build_paper_response, app


class WebRankingTests(unittest.TestCase):
    def test_paper_response_contains_direct_ranking_controls(self):
        paper = {
            "id": "paper-1",
            "title": "虚拟电厂中的能源具身智能",
            "abstract": "能源智能体感知储能系统并控制源网荷储协同。",
            "authors": ["研究者"],
            "published": "2026-07-10",
            "categories": ["eess.SY"],
            "entry_url": "https://arxiv.org/abs/2607.00001",
            "pdf_url": "https://arxiv.org/pdf/2607.00001",
        }
        result = _build_paper_response(paper, {"id": "paper-1", "summary": "中文摘要"})
        card = result["web_card"]

        self.assertEqual(card["summary"], "中文摘要")
        self.assertIn(card["read_priority"], {"high", "medium", "low"})
        self.assertIn(card["recommended_action"], {"精读", "略读", "存档"})
        self.assertIsInstance(card["importance_score"], float)
        self.assertEqual(len(card["ranking_score_breakdown"]), 5)

    def test_index_contains_priority_filter_and_relevance_sort(self):
        response = app.test_client().get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="paper-priority-filter"', html)
        self.assertIn('value="relevance"', html)
        self.assertIn("中国能源具身智能信息收集平台", html)

    def test_papers_api_defaults_to_relevance_order(self):
        papers = {
            "date": "2026-07-14",
            "papers": [
                {"id": "other", "title": "无关内容", "categories": []},
                {
                    "id": "energy",
                    "title": "虚拟电厂能源具身智能",
                    "abstract": "能源智能体控制储能系统。",
                    "categories": ["eess.SY"],
                },
            ],
        }
        with patch("src.web.app._load_papers_data", return_value=papers), patch(
            "src.web.app._load_summaries_by_id", return_value={}
        ):
            response = app.test_client().get("/api/papers")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["papers"][0]["id"], "energy")


if __name__ == "__main__":
    unittest.main()
