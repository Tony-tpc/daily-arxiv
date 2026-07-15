"""End-to-end regression from durable snapshots to temporal trend signals."""

import tempfile
import unittest

from src.analyzer.trend_analyzer import TrendAnalyzer
from src.storage.base import JSONStorage


class HistoryTrendRegressionTests(unittest.TestCase):
    def test_json_snapshots_drive_cross_source_emergence_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(temp_dir)
            storage.save_snapshot([
                _document("paper-old", "paper", "传统调度", "煤电调度")
            ], snapshot_date="2026-07-01")
            storage.save_snapshot([
                _document("policy-new", "policy", "虚拟电厂", "国家能源局")
            ], snapshot_date="2026-07-09")
            storage.save_snapshot([
                _document("news-new", "news", "虚拟电厂", "国家电网"),
                _document("report-new", "industry_report", "能源智能体", "电力规划设计总院"),
            ], snapshot_date="2026-07-14")

            history = storage.query_history(
                date_from="2026-07-01",
                date_to="2026-07-14",
            )
            analyzer = TrendAnalyzer.__new__(TrendAnalyzer)
            analyzer.config = {"analysis": {"trend_window_days": [7, 30, 60]}}
            result = analyzer.analyze_temporal(history, as_of="2026-07-14")

        seven_day = result["windows"]["7"]
        emerging = {item["name"] for item in seven_day["new_topic_emergence"]}
        self.assertEqual(result["observation_count"], 4)
        self.assertEqual(seven_day["current_document_count"], 3)
        self.assertEqual(seven_day["previous_document_count"], 1)
        self.assertIn("虚拟电厂", emerging)
        self.assertEqual(
            seven_day["cross_source_comparison"]["source_counts"],
            {"policy": 1, "news": 1, "industry_report": 1},
        )
        self.assertEqual([point["date"] for point in result["timeline"]], [
            "2026-07-01", "2026-07-09", "2026-07-10", "2026-07-14"
        ])


def _document(document_id, source_type, topic, organization):
    published_dates = {
        "paper-old": "2026-07-01",
        "policy-new": "2026-07-09",
        "news-new": "2026-07-10",
        "report-new": "2026-07-14",
    }
    return {
        "id": document_id,
        "published_at": published_dates[document_id],
        "source_type": source_type,
        "title": f"{topic}研究",
        "tags": [topic],
        "research_direction": [topic],
        "entities": [organization],
    }


if __name__ == "__main__":
    unittest.main()
