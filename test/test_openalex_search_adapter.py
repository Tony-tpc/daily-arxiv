"""Unit tests for topic-based OpenAlex paper discovery."""

import unittest
from unittest.mock import patch

import httpx

from src.sources.openalex_search_adapter import OpenAlexSearchAdapter


class OpenAlexSearchAdapterTests(unittest.TestCase):
    def test_fetch_maps_energy_paper_and_rejects_survey(self):
        def handler(request):
            self.assertEqual(request.url.path, "/works")
            self.assertEqual(request.url.params["search"], "energy agent")
            return httpx.Response(200, json={"results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1000/energy.1",
                    "display_name": "Multi-Agent Coordination for Virtual Power Plants",
                    "publication_year": 2026,
                    "cited_by_count": 28,
                    "primary_topic": {"display_name": "Energy systems"},
                    "topics": [{"display_name": "Virtual power plant"}],
                    "concepts": [{"display_name": "Electric power system"}],
                    "authorships": [{
                        "author": {"display_name": "Wei Zhang"},
                        "institutions": [{"display_name": "Tsinghua University"}],
                    }],
                    "referenced_works_count": 5,
                    "ids": {},
                    "updated_date": "2026-07-10",
                },
                {
                    "id": "https://openalex.org/W2",
                    "display_name": "A Survey of Energy Markets",
                    "publication_year": 2026,
                    "cited_by_count": 100,
                    "topics": [],
                    "concepts": [],
                    "authorships": [],
                    "ids": {},
                },
            ]})

        config = {
            "app": {"language": "zh"},
            "sources": {
                "openalex": {"api_key": "test-key"},
                "openalex_search": {
                    "enabled": True,
                    "search_terms": ["energy agent"],
                    "max_results": 5,
                },
            },
        }
        adapter = OpenAlexSearchAdapter(config)
        adapter.client.close()
        adapter.client = httpx.Client(transport=httpx.MockTransport(handler))

        with patch.object(adapter, "save_raw_snapshot"):
            records = adapter.fetch()
        adapter.client.close()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "W1")
        self.assertEqual(records[0]["doi"], "10.1000/energy.1")
        self.assertEqual(records[0]["impact_bracket"], "high")
        self.assertEqual(records[0]["openalex_institutions"], ["Tsinghua University"])

        normalized = adapter.normalize(records)
        self.assertEqual(normalized[0]["source_type"], "paper")
        self.assertEqual(normalized[0]["source_name"], "OpenAlex")
        self.assertEqual(normalized[0]["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
