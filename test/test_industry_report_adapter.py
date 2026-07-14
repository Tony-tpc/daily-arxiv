"""Tests for industry report normalization and LLM trend extraction."""

import unittest
from unittest.mock import Mock, patch

from src.sources.industry_report_adapter import IndustryReportSourceAdapter


class IndustryReportSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tracking_topics": ["energy storage"],
            "keyword_groups": [{"name": "markets", "terms": ["electricity market"]}],
            "sources": {
                "industry_report": {
                    "enabled": True,
                    "regions": ["CN"],
                    "feeds": [
                        {
                            "name": "Grid Institute",
                            "url": "https://reports.example/feed",
                            "institution": "Grid Institute",
                            "keywords": ["power sector"],
                        }
                    ],
                    "llm_extraction": {"enabled": False},
                }
            },
        }

    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_normalize_extracts_report_fields(self, _client, _load_json):
        adapter = IndustryReportSourceAdapter(self.config)
        document = adapter.normalize([self._record()])[0]

        self.assertEqual(document["source_type"], "industry_report")
        self.assertEqual(document["institution"], "Grid Institute")
        self.assertEqual(document["report_type"], "market_outlook")
        self.assertEqual(document["region"], "CN")
        self.assertIn("energy storage", document["topic_directions"])
        self.assertIn("markets", document["topic_directions"])
        self.assertIn("power sector", document["keywords"])

    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_llm_progress_and_trends_are_schema_fields(self, _client, _load_json):
        llm_client = Mock()
        llm_client.generate.return_value = json_response = (
            '{"industry_progress":"Pilots doubled","trend_assessment":"Deployment is accelerating",'
            '"topic_directions":["VPP"],"keywords":["aggregator"]}'
        )
        self.config["sources"]["industry_report"]["llm_extraction"] = {"enabled": True}
        adapter = IndustryReportSourceAdapter(self.config, llm_client=llm_client)

        document = adapter.normalize([self._record()])[0]

        self.assertEqual(document["industry_progress"], "Pilots doubled")
        self.assertEqual(document["trend_assessment"], "Deployment is accelerating")
        self.assertIn("VPP", document["topic_directions"])
        self.assertIn("aggregator", document["keywords"])
        llm_client.generate.assert_called_once()

    @patch("src.sources.industry_report_adapter.save_json")
    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_fetch_collects_filtered_chinese_html_reports(
        self, client_class, _load_json, _save_json
    ):
        self.config["sources"]["industry_report"]["feeds"] = [{
            "name": "国家能源局可靠性和质监中心",
            "url": "https://reports.example/list",
            "format": "html",
            "item_selector": "dl.dl_l",
            "link_selector": "dt a[href]",
            "date_selector": "dd span",
            "detail_content_selector": ".article-content",
            "institution": "国家能源局",
            "region": "CN",
            "title_keywords_any": ["报告"],
            "title_keywords_exclude": ["预算"],
        }]
        listing = self._response(
            b'<dl class="dl_l"><dt><a href="/report">2025 Energy Report \xe6\x8a\xa5\xe5\x91\x8a</a></dt>'
            b'<dd><span>\xe6\x97\xa5\xe6\x9c\x9f\xef\xbc\x9a2026-07-01</span></dd></dl>'
            b'<dl class="dl_l"><dt><a href="/budget">2026 \xe9\xa2\x84\xe7\xae\x97\xe6\x8a\xa5\xe5\x91\x8a</a></dt></dl>'
        )
        detail = self._response(b'<div class="article-content">China power market evidence.</div>')
        client_class.return_value.get.side_effect = [listing, detail]
        adapter = IndustryReportSourceAdapter(self.config)

        records = adapter.fetch()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["published_at"], "2026-07-01")
        self.assertEqual(records[0]["region"], "CN")
        self.assertIn("power market evidence", records[0]["content"])

    @staticmethod
    def _record():
        return {
            "entry_id": "report-1",
            "dedup_key": "report123",
            "title": "Global electricity market outlook",
            "summary": "Market evidence.",
            "content": "Energy storage participation in the electricity market is rising.",
            "url": "https://reports.example/one",
            "feed_url": "https://reports.example/feed",
            "source_name": "Grid Institute",
            "published_at": "2026-07-01T00:00:00+00:00",
            "collected_at": "2026-07-14T00:00:00+00:00",
            "region": "",
            "tags": ["flexibility"],
        }

    @staticmethod
    def _response(content, status_code=200, headers=None):
        response = Mock()
        response.content = content
        response.status_code = status_code
        response.headers = headers or {}
        response.raise_for_status.return_value = None
        return response


if __name__ == "__main__":
    unittest.main()
