"""Tests for evidence-first trend forecasting and scenarios."""

import unittest

from src.analyzer.forecast_analyzer import ForecastAnalyzer


class ForecastAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = ForecastAnalyzer({
            "analysis": {
                "forecast": {
                    "history_months": 24,
                    "min_quant_months": 12,
                    "min_nonzero_months": 6,
                    "min_topic_documents": 12,
                    "strategic_min_months": 18,
                    "strategic_min_documents": 24,
                    "random_state": 42,
                }
            }
        })

    def test_sparse_history_yields_low_confidence_falsifiable_scenario(self):
        result = self.analyzer.analyze([
            _observation("one", "paper", "2026-07-01", "Energy agent control", 99)
        ], as_of="2026-07-15")

        forecast = _forecast(result, "autonomous_control")
        scenario = _scenario(result, "autonomous_control")
        self.assertEqual(len(result["taxonomy"]), 6)
        self.assertEqual(forecast["mode"], "scenario_only")
        self.assertEqual(forecast["confidence"], "low")
        self.assertTrue(forecast["data_gaps"])
        self.assertTrue(forecast["counter_signals"])
        self.assertTrue(forecast["watch_indicators"])
        self.assertIn("one", forecast["evidence_ids"])
        self.assertNotIn("importance_score", forecast["metrics"])
        self.assertTrue(scenario["downside"])

    def test_quantitative_forecast_is_deterministic_and_has_80_percent_band(self):
        observations = []
        for index, month in enumerate(_months("2025-02", 18)):
            topic_count = 1 + index // 6
            for number in range(topic_count):
                observations.append(_observation(
                    f"topic-{month}-{number}", "paper", f"{month}-05",
                    "Multi-agent reinforcement learning for power systems",
                ))
            for number in range(5):
                observations.append(_observation(
                    f"filler-{month}-{number}", "paper", f"{month}-10",
                    "Power system operations baseline",
                ))

        first = self.analyzer.analyze(observations, as_of="2026-07-15")
        second = self.analyzer.analyze(observations, as_of="2026-07-15")
        forecast = _forecast(first, "multi_agent_rl")

        self.assertEqual(forecast["mode"], "quantitative")
        self.assertEqual(forecast["confidence"], "medium")
        self.assertEqual([item["months_ahead"] for item in forecast["projections"]], [1, 3])
        self.assertLessEqual(forecast["projections"][0]["lower"], forecast["projections"][0]["upper"])
        self.assertEqual(forecast, _forecast(second, "multi_agent_rl"))

    def test_partial_coverage_without_documents_is_not_converted_to_zero(self):
        coverage = {
            "entries": {
                "rss:2026-06": {"period": "2026-06", "status": "partial"}
            }
        }

        result = self.analyzer.analyze([], coverage=coverage, as_of="2026-07-15")

        self.assertEqual(result["data_quality"]["history_month_count"], 0)
        self.assertIn("partial", result["data_quality"]["coverage_status_counts"])

    def test_cross_source_sequence_requires_repeated_evidence(self):
        observations = [
            _observation("p1", "paper", "2026-01-05", "Virtual power plant control"),
            _observation("p2", "paper", "2026-02-05", "Virtual power plant control"),
            _observation("g1", "policy", "2026-03-05", "虚拟电厂政策"),
            _observation("g2", "policy", "2026-04-05", "虚拟电厂政策"),
            _observation("n1", "news", "2026-05-05", "虚拟电厂示范"),
            _observation("n2", "news", "2026-06-05", "虚拟电厂示范"),
        ]

        result = self.analyzer.analyze(observations, as_of="2026-07-15")
        lead_lag = next(
            item for item in result["lead_lag"]
            if item["topic_id"] == "grid_coordination"
        )

        self.assertEqual(lead_lag["status"], "supported")
        self.assertEqual(
            [item["source_type"] for item in lead_lag["sequence"]],
            ["paper", "policy", "news"],
        )
        self.assertEqual(lead_lag["lag_months"], 4)


def _observation(document_id, source_type, published_at, title, importance=0):
    return {
        "snapshot_date": "2026-07-15",
        "document": {
            "id": document_id,
            "source_type": source_type,
            "title": title,
            "published_at": published_at,
            "importance_score": importance,
        },
    }


def _months(start, count):
    year, month = (int(value) for value in start.split("-"))
    result = []
    for offset in range(count):
        absolute = year * 12 + month - 1 + offset
        current_year, zero_month = divmod(absolute, 12)
        result.append(f"{current_year:04d}-{zero_month + 1:02d}")
    return result


def _forecast(result, topic_id):
    return next(item for item in result["forecasts"] if item["topic_id"] == topic_id)


def _scenario(result, topic_id):
    return next(item for item in result["scenarios"] if item["topic_id"] == topic_id)


if __name__ == "__main__":
    unittest.main()
