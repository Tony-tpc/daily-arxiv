"""Tests for the forecast API filters and backward-compatible loading."""

import unittest
from pathlib import Path
from unittest.mock import patch

from src.web import app as web_app


class WebForecastTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_forecast_api_filters_horizon_topic_and_confidence(self):
        payload = {
            "schema_version": "2.0",
            "as_of": "2026-07-15",
            "taxonomy": [
                {"id": "grid_coordination", "label": "源网荷储与虚拟电厂协同"},
                {"id": "market_game", "label": "电力市场与博弈机制"},
            ],
            "data_quality": {},
            "topic_series": {"grid_coordination": [], "market_game": []},
            "forecasts": [
                {"topic_id": "grid_coordination", "confidence": "low"},
                {"topic_id": "market_game", "confidence": "medium"},
            ],
            "scenarios": [
                {"topic_id": "grid_coordination", "confidence": "low"},
                {"topic_id": "market_game", "confidence": "medium"},
            ],
            "lead_lag": [
                {"topic_id": "grid_coordination"},
                {"topic_id": "market_game"},
            ],
        }
        with patch.object(
            web_app, "load_json", return_value={"trend_forecast": payload}
        ):
            response = self.client.get(
                "/api/trends/forecast?horizon=strategic&topic=虚拟电厂&confidence=low"
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["forecasts"], [])
        self.assertEqual([item["topic_id"] for item in data["scenarios"]], ["grid_coordination"])
        self.assertEqual(list(data["topic_series"]), ["grid_coordination"])

    def test_narrative_dashboard_exposes_tabs_long_form_and_evidence_drawer(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for element_id in (
            "narrative-coverage", "narrative-toc", "narrative-content",
            "narrative-opportunities", "narrative-chains",
            "narrative-evidence-drawer", "narrative-evidence-body",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn('data-narrative-view="paper"', html)
        self.assertIn('data-narrative-view="multi_source"', html)
        self.assertNotIn('id="forecast-topic-cards"', html)

        script = (Path(__file__).resolve().parents[1] / "static" / "js" / "main.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("async function loadNarrative", script)
        self.assertIn("function renderNarrativeChains", script)
        self.assertIn("const forecastSignals", script)
        self.assertIn("Compatibility fallback", script)

    def test_forecast_api_rejects_invalid_filters(self):
        self.assertEqual(
            self.client.get("/api/trends/forecast?horizon=weekly").status_code,
            400,
        )
        self.assertEqual(
            self.client.get("/api/trends/forecast?confidence=certain").status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
