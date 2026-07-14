"""Tests for the visual scheduler-status API."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.web.app import app


class WebSchedulerStatusTests(unittest.TestCase):
    def test_status_api_combines_schedule_and_last_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            status_path = Path(temp_dir, "scheduler_status.json")
            status_path.write_text(json.dumps({
                "updated_at": "2026-07-14T10:00:00+00:00",
                "jobs": {"news_8h": {"status": "succeeded", "record_count": 4}},
            }), encoding="utf-8")
            config = {
                "scheduler": {
                    "enabled": True,
                    "timezone": "Asia/Shanghai",
                    "status_path": str(status_path),
                }
            }
            with patch("src.web.app.config", config):
                response = app.test_client().get("/api/scheduler/status")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload["jobs"]), 4)
        news = next(item for item in payload["jobs"] if item["id"] == "news_8h")
        self.assertEqual(news["status"], "succeeded")
        self.assertEqual(news["schedule"], "每 8 小时")


if __name__ == "__main__":
    unittest.main()
