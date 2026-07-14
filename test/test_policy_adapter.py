"""Tests for policy field extraction and LLM enrichment."""

import unittest
from unittest.mock import Mock, patch

from src.sources.policy_adapter import PolicySourceAdapter


class PolicySourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tracking_topics": ["virtual power plant"],
            "keyword_groups": [{"name": "markets", "terms": ["electricity market"]}],
            "sources": {
                "policy": {
                    "enabled": True,
                    "feeds": [
                        {
                            "name": "Energy Ministry",
                            "url": "https://policy.example/feed",
                            "issuing_body": "Energy Ministry",
                            "policy_level": "national",
                            "region": "CN",
                        }
                    ],
                    "llm_extraction": {"enabled": False},
                }
            },
        }

    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_normalize_extracts_policy_standard_fields(self, _client, _load_json):
        adapter = PolicySourceAdapter(self.config)
        document = adapter.normalize([self._record()])[0]

        self.assertEqual(document["source_type"], "policy")
        self.assertEqual(document["issuing_body"], "Energy Ministry")
        self.assertEqual(document["document_type"], "regulation")
        self.assertEqual(document["effective_date"], "2026-08-01")
        self.assertEqual(document["policy_strength"], "high")
        self.assertIn("virtual power plant", document["impact_areas"])
        self.assertIn("markets", document["impact_areas"])

    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_llm_insights_are_explicit_schema_fields(self, _client, _load_json):
        llm_client = Mock()
        llm_client.generate.return_value = """```json
        {"core_policy_direction":"flexibility markets","technology_directions":["VPP","storage"],
         "potential_impact":"More aggregator participation","impact_areas":["demand response"]}
        ```"""
        self.config["sources"]["policy"]["llm_extraction"] = {"enabled": True, "max_tokens": 500}
        adapter = PolicySourceAdapter(self.config, llm_client=llm_client)

        document = adapter.normalize([self._record()])[0]

        self.assertEqual(document["core_policy_direction"], "flexibility markets")
        self.assertEqual(document["technology_directions"], ["VPP", "storage"])
        self.assertEqual(document["potential_impact"], "More aggregator participation")
        self.assertTrue(document["provenance"]["metadata"]["llm_extracted"])

    @patch("src.sources.policy_adapter.save_json")
    @patch("src.sources.rss_adapter.load_json", return_value=None)
    @patch("src.sources.rss_adapter.httpx.Client")
    def test_fetch_collects_official_html_listing_and_deduplicates(
        self, client_class, _load_json, _save_json
    ):
        self.config["sources"]["policy"]["feeds"] = [
            {
                "name": "国家能源局",
                "url": "https://policy.example/list",
                "format": "html",
                "item_selector": ".policy-list li",
                "link_selector": "a[href]",
                "date_selector": "span",
                "detail_content_selector": ".article-content",
                "issuing_body": "国家能源局",
                "region": "CN",
            }
        ]
        listing = self._response(
            b'<ul class="policy-list"><li><a href="/one">Policy one</a><span>2026/07/10</span></li></ul>',
            headers={"ETag": '"cn-v1"'},
        )
        detail = self._response(b'<main class="article-content"><p>Binding energy policy.</p></main>')
        client = client_class.return_value
        client.get.side_effect = [listing, detail, listing]
        adapter = PolicySourceAdapter(self.config)

        first = adapter.fetch()
        second = adapter.fetch()

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(first[0]["content"], "Binding energy policy.")
        self.assertEqual(first[0]["published_at"], "2026-07-10")
        self.assertEqual(client.get.call_args_list[2].kwargs["headers"]["If-None-Match"], '"cn-v1"')

    @staticmethod
    def _record():
        return {
            "entry_id": "policy-1",
            "dedup_key": "abc123",
            "title": "Virtual power plant electricity market regulation",
            "summary": "Binding market requirements.",
            "content": "Operators must comply. Effective date: 2026-08-01.",
            "url": "https://policy.example/one",
            "feed_url": "https://policy.example/feed",
            "source_name": "Energy Ministry",
            "published_at": "2026-07-01T00:00:00+00:00",
            "collected_at": "2026-07-14T00:00:00+00:00",
            "region": "CN",
            "tags": ["power system"],
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
