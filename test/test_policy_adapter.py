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


if __name__ == "__main__":
    unittest.main()
