#!/usr/bin/env python3
"""Tests for OpenAlex enrichment behavior."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sources.openalex_adapter import OpenAlexAdapter


class OpenAlexAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'sources': {
                'openalex': {
                    'enabled': True,
                    'api_key': '',
                    'request_timeout_seconds': 20,
                    'cache_path': 'data/cache/test_openalex_cache.json',
                    'max_title_search_results': 5,
                    'select_fields': ['id', 'doi', 'display_name', 'cited_by_count', 'topics', 'primary_topic', 'authorships', 'referenced_works', 'referenced_works_count', 'updated_date'],
                }
            }
        }

    @patch('src.sources.openalex_adapter.save_json')
    @patch('src.sources.openalex_adapter.load_json', return_value=None)
    @patch('src.sources.openalex_adapter.httpx.Client')
    def test_enrich_record_prefers_doi_lookup(self, client_cls, _load_json, _save_json):
        client = Mock()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            'id': 'https://openalex.org/W123',
            'doi': 'https://doi.org/10.1000/example',
            'cited_by_count': 42,
            'primary_topic': {'display_name': 'Energy systems'},
            'topics': [{'display_name': 'Energy systems'}],
            'authorships': [{'institutions': [{'display_name': 'Tsinghua University'}]}],
            'referenced_works': ['https://openalex.org/W456'],
            'referenced_works_count': 1,
            'updated_date': '2026-01-01',
        }
        response.raise_for_status.return_value = None
        client.get.return_value = response
        client_cls.return_value = client

        adapter = OpenAlexAdapter(self.config)
        enriched = adapter.enrich_record({'id': '2501.00001', 'title': 'Paper', 'doi': 'doi:10.1000/example'})

        self.assertEqual(enriched['openalex_id'], 'https://openalex.org/W123')
        self.assertEqual(enriched['citation_count'], 42)
        self.assertIn('Tsinghua University', enriched['openalex_institutions'])
        self.assertEqual(enriched['doi'], '10.1000/example')

    @patch('src.sources.openalex_adapter.save_json')
    @patch('src.sources.openalex_adapter.load_json', return_value=None)
    @patch('src.sources.openalex_adapter.httpx.Client')
    def test_title_fallback_uses_search_results(self, client_cls, _load_json, _save_json):
        client = Mock()
        miss_response = Mock()
        miss_response.status_code = 404
        miss_response.raise_for_status.return_value = None

        search_response = Mock()
        search_response.status_code = 200
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {
            'results': [
                {
                    'id': 'https://openalex.org/W999',
                    'display_name': 'OpenAlex Guided Power Systems',
                    'cited_by_count': 5,
                    'topics': [],
                    'authorships': [],
                    'referenced_works': [],
                    'referenced_works_count': 0,
                    'updated_date': '2026-01-01',
                }
            ]
        }
        client.get.side_effect = [miss_response, search_response]
        client_cls.return_value = client

        adapter = OpenAlexAdapter(self.config)
        enriched = adapter.enrich_record({'id': '2501.00001', 'title': 'OpenAlex Guided Power Systems'})

        self.assertEqual(enriched['openalex_id'], 'https://openalex.org/W999')
        self.assertEqual(enriched['citation_count'], 5)
