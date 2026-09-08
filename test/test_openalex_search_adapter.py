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
                    "type": "article",
                    "primary_location": {"source": {
                        "display_name": "IEEE Transactions on Smart Grid",
                        "issn_l": "1949-3053",
                        "issn": ["1949-3053"],
                    }},
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
        self.assertEqual(records[0]["publication_type"], "article")
        self.assertEqual(records[0]["journal_issn_l"], "1949-3053")

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

    def test_rate_limit_uses_crossref_metadata_then_whitelist(self):
        def handler(request):
            if request.url.host == "api.openalex.org":
                return httpx.Response(429, json={"error": "rate limited"})
            self.assertEqual(request.url.host, "api.crossref.org")
            return httpx.Response(200, json={"message": {"items": [
                {
                    "DOI": "10.1109/tsg.2026.1",
                    "title": ["Safe energy control for virtual power plants"],
                    "container-title": ["IEEE Transactions on Smart Grid"],
                    "ISSN": ["1949-3053", "1949-3061"],
                    "type": "journal-article",
                    "published": {"date-parts": [[2026, 7, 1]]},
                    "author": [{"given": "Wei", "family": "Zhang"}],
                    "publisher": "IEEE",
                    "URL": "https://doi.org/10.1109/tsg.2026.1",
                },
                {
                    "DOI": "10.1000/unknown",
                    "title": ["Unknown energy journal control"],
                    "container-title": ["Unknown Energy Journal"],
                    "ISSN": ["0000-0000"],
                    "type": "journal-article",
                    "published": {"date-parts": [[2026, 7]]},
                },
            ]}})

        config = {
            "sources": {
                "openalex_search": {
                    "search_terms": ["virtual power plant reinforcement learning"],
                    "max_results": 10,
                    "crossref_fallback": {"enabled": True, "rows_per_query": 10},
                },
            },
            "paper_quality": {
                "enabled": True,
                "approved_venues": [{
                    "id": "ieee_tsg",
                    "name": "IEEE Transactions on Smart Grid",
                    "issn_l": "1949-3053",
                    "quartile": "Q1",
                }],
            },
        }
        adapter = OpenAlexSearchAdapter(config)
        adapter.client.close()
        adapter.client = httpx.Client(transport=httpx.MockTransport(handler))

        with patch.object(adapter, "save_raw_snapshot"):
            records = adapter.fetch()
        adapter.client.close()
        papers = adapter.normalize(records)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["source_name"], "Crossref")
        self.assertEqual(records[0]["published"], "2026-07-01")
        self.assertEqual(records[0]["journal_issn_l"], "1949-3053")
        self.assertEqual([paper["doi"] for paper in papers], ["10.1109/tsg.2026.1"])
        self.assertEqual(papers[0]["quality_gate"]["quartile"], "Q1")


if __name__ == "__main__":
    unittest.main()
