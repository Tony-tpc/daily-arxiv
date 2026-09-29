#!/usr/bin/env python3
"""Regression coverage for the canonical paper directory."""

import unittest
from unittest.mock import patch

from src.web import app as web_app
from test.test_paper_quality import QUALITY_CONFIG


class WebPaperDirectoryTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()
        patcher = patch.dict(web_app.config, {**QUALITY_CONFIG, 'paper_discovery': {'enabled': False}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_paper_directory_prefers_canonical_snapshot(self):
        canonical = [{
            'id': 'canonical-paper',
            'schema_version': '1.0',
            'source_type': 'paper',
            'source_name': 'arXiv',
            'title': 'Energy agent for virtual power plant control',
            'published_at': '2026-07-14',
            'categories': ['eess.SY'],
            'publication_type': 'article',
            'journal_name': 'IEEE Transactions on Smart Grid',
            'journal_issn_l': '1949-3053',
        }, {
            'id': 'unverified-paper',
            'schema_version': '1.0',
            'source_type': 'paper',
            'source_name': 'OpenAlex',
            'title': 'Unverified Energy Paper',
            'published_at': '2026-07-14',
            'categories': ['eess.SY'],
            'publication_type': 'article',
            'journal_name': 'Unknown Energy Journal',
            'journal_issn_l': '0000-0000',
        }]
        legacy = {
            'papers': [{
                'id': 'legacy-robot',
                'title': '<span>Power dispatch robot</span>',
                'categories': ['cs.RO'],
            }]
        }

        with patch.object(web_app, '_load_intelligence_documents', return_value=canonical), patch.object(
            web_app, 'load_json', return_value=legacy
        ) as mocked_load:
            response = self.client.get('/api/papers')

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['papers'][0]['id'], 'canonical-paper')
        self.assertEqual(payload['papers'][0]['source_type'], 'paper')
        mocked_load.assert_called_once_with('data/summaries/latest.json')

    def test_legacy_fallback_is_normalized_and_scope_filtered(self):
        legacy = {
            'date': '2026-07-14',
            'papers': [
                {
                    'id': 'energy-paper',
                    'title': '&lt;span&gt;Energy agent control&lt;/span&gt;',
                    'abstract': 'Virtual power plant and energy storage coordination.',
                    'categories': ['eess.SY'],
                    'publication_type': 'article',
                    'journal_name': 'IEEE Transactions on Smart Grid',
                    'journal_issn_l': '1949-3053',
                },
                {
                    'id': 'robot-paper',
                    'title': 'Robot arm control for power equipment',
                    'categories': ['cs.RO'],
                },
            ],
        }

        def load_json(path):
            if path == 'data/papers/latest_openalex.json':
                return legacy
            return {}

        with patch.object(web_app, '_load_intelligence_documents', return_value=[]), patch.object(
            web_app, 'load_json', side_effect=load_json
        ):
            payload = self.client.get('/api/papers').get_json()

        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['papers'][0]['title'], 'Energy agent control')
        self.assertEqual(payload['papers'][0]['source_type'], 'paper')

    def test_legacy_summary_cannot_overwrite_canonical_identity(self):
        paper = {
            'id': 'canonical-paper',
            'schema_version': '1.0',
            'source_type': 'paper',
            'source_name': 'OpenAlex',
            'title': 'Canonical energy-agent paper',
            'summary': '',
            'categories': ['eess.SY'],
        }
        legacy_summary = {
            'id': 'legacy-id',
            'schema_version': '0.1',
            'source_type': 'robot',
            'title': 'Legacy robot title',
            'summary': 'Useful Chinese summary.',
        }

        result = web_app._build_document_from_paper(paper, legacy_summary)

        self.assertEqual(result['id'], 'canonical-paper')
        self.assertEqual(result['schema_version'], '1.0')
        self.assertEqual(result['source_type'], 'paper')
        self.assertEqual(result['title'], 'Canonical energy-agent paper')
        self.assertEqual(result['summary'], 'Useful Chinese summary.')


if __name__ == '__main__':
    unittest.main()
