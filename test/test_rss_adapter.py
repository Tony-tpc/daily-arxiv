"""Tests for RSS/Atom collection, conditional requests, and normalization."""

import unittest
from unittest.mock import Mock, patch

from src.sources.rss_adapter import RSSSourceAdapter


RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Energy News</title>
<item><guid>news-1</guid><title>Grid &amp; storage update</title>
<link>https://example.com/story/</link><description><![CDATA[<p>Storage expanded.</p>]]></description>
<pubDate>Mon, 13 Jul 2026 08:00:00 GMT</pubDate><category>storage</category></item>
</channel></rss>"""

ATOM_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Policy Lab</title>
<entry><id>policy-1</id><title>Market design study</title>
<link href="https://example.org/study"/><updated>2026-07-13T10:00:00Z</updated>
<summary>New market evidence.</summary></entry></feed>"""


class RSSSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "sources": {
                "rss": {
                    "enabled": True,
                    "feeds": [
                        {"name": "Energy News", "url": "https://example.com/rss", "region": "US"},
                        {"name": "Policy Lab", "url": "https://example.org/atom"},
                    ],
                    "state_path": "data/state/test_rss.json",
                    "snapshot_dir": "data/raw/test_rss",
                }
            }
        }

    @patch("src.sources.rss_adapter.save_json")
    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_fetch_supports_rss_and_atom(self, client_class, _load_json, _save_json):
        responses = [self._response(RSS_XML), self._response(ATOM_XML)]
        client_class.return_value.get.side_effect = responses

        adapter = RSSSourceAdapter(self.config)
        records = adapter.fetch()

        self.assertEqual([record["title"] for record in records], ["Grid & storage update", "Market design study"])
        self.assertEqual(records[0]["tags"], ["storage"])

    @patch("src.sources.rss_adapter.save_json")
    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_conditional_headers_and_seen_hash_prevent_reprocessing(
        self, client_class, _load_json, _save_json
    ):
        first = self._response(RSS_XML, headers={"ETag": '"v1"', "Last-Modified": "Mon, 13 Jul 2026 08:00:00 GMT"})
        second = self._response(b"", status_code=304)
        client = client_class.return_value
        client.get.side_effect = [first, second]
        self.config["sources"]["rss"]["feeds"] = [self.config["sources"]["rss"]["feeds"][0]]

        adapter = RSSSourceAdapter(self.config)
        self.assertEqual(len(adapter.fetch()), 1)
        self.assertEqual(adapter.fetch(), [])

        second_headers = client.get.call_args_list[1].kwargs["headers"]
        self.assertEqual(second_headers["If-None-Match"], '"v1"')
        self.assertIn("If-Modified-Since", second_headers)
        self.assertEqual(len(adapter.state["seen"]), 1)

    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_normalize_maps_news_schema(self, client_class, _load_json):
        adapter = RSSSourceAdapter(self.config)
        record = adapter._raw_entry(
            {"id": "one", "title": "A story", "link": "https://example.com/a", "summary": "Details"},
            self.config["sources"]["rss"]["feeds"][0],
            "https://example.com/rss",
            "Energy News",
            "2026-07-14T00:00:00+00:00",
        )

        document = adapter.normalize([record])[0]

        self.assertEqual(document["source_type"], "news")
        self.assertEqual(document["media_name"], "Energy News")
        self.assertEqual(document["provenance"]["collected_via"], "rss")

    @patch("src.sources.rss_adapter.save_json")
    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_keyword_filters_keep_energy_news_and_exclude_robotics(
        self, client_class, _load_json, _save_json
    ):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><title>国内科技</title>
        <item><guid>1</guid><title>电力市场推进虚拟电厂建设</title><link>https://cn.example/energy</link></item>
        <item><guid>2</guid><title>人形机器人机械臂发布</title><link>https://cn.example/robot</link><description>能源演示</description></item>
        <item><guid>3</guid><title>消费市场动态</title><link>https://cn.example/other</link></item>
        </channel></rss>""".encode("utf-8")
        client_class.return_value.get.return_value = self._response(xml)
        self.config["sources"]["rss"]["feeds"] = [self.config["sources"]["rss"]["feeds"][0]]
        self.config["sources"]["rss"]["include_keywords"] = ["电力", "能源"]
        self.config["sources"]["rss"]["exclude_keywords"] = ["机械臂", "人形机器人"]

        records = RSSSourceAdapter(self.config).fetch()

        self.assertEqual([record["entry_id"] for record in records], ["1"])

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
