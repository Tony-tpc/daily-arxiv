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

    def test_fetch_range_uses_date_filters_and_cursor_pagination(self):
        cursors = []

        def handler(request):
            cursors.append(request.url.params["cursor"])
            self.assertIn("from_publication_date:2025-07-01", request.url.params["filter"])
            self.assertIn("to_publication_date:2025-07-31", request.url.params["filter"])
            page = len(cursors)
            return httpx.Response(200, json={
                "results": [{
                    "id": f"https://openalex.org/W{page}",
                    "display_name": f"Energy agent control {page}",
                    "publication_date": f"2025-07-0{page}",
                    "cited_by_count": 1,
                    "primary_topic": {"display_name": "Energy systems"},
                    "topics": [{"display_name": "Electric power system"}],
                    "concepts": [{"display_name": "Electric power system"}],
                    "authorships": [],
                    "ids": {},
                }],
                "meta": {"next_cursor": "next" if page == 1 else None},
            })

        config = {
            "sources": {
                "openalex": {"api_key": "test-key"},
                "openalex_search": {
                    "topic_query": "energy agent",
                    "per_page": 100,
                    "backfill_concept_id": "C89227174",
                },
            },
        }
        adapter = OpenAlexSearchAdapter(config)
        adapter.client.close()
        adapter.client = httpx.Client(transport=httpx.MockTransport(handler))

        records = adapter.fetch_range("2025-07-01", "2025-07-31")
        adapter.client.close()

        self.assertEqual(cursors, ["*", "next"])
        self.assertEqual([record["published"] for record in records], [
            "2025-07-01", "2025-07-02"
        ])


if __name__ == "__main__":
    unittest.main()
