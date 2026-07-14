#!/usr/bin/env python3
"""Tests for the read-only Zotero Local API integration."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import httpx


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integrations.zotero_client import (
    ZoteroClient,
    ZoteroLocalAPIError,
    generate_citekey,
)


class ZoteroClientTests(unittest.TestCase):
    def test_local_api_uses_get_api_v3_and_user_zero(self):
        def handler(request):
            self.assertEqual(request.method, 'GET')
            self.assertEqual(request.url.path, '/api/users/0/items/top')
            self.assertEqual(request.headers['Zotero-API-Version'], '3')
            self.assertEqual(request.url.params['q'], 'virtual power plant')
            return httpx.Response(200, json=[{'key': 'ABC', 'data': {'title': 'Paper'}}])

        client = ZoteroClient(_config(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        items = client.list_items(query='virtual power plant', limit=10)

        self.assertEqual(items[0]['key'], 'ABC')

    def test_exports_existing_local_library_as_csljson_and_bibtex(self):
        def handler(request):
            if request.url.params['format'] == 'csljson':
                return httpx.Response(200, json=[{'id': 'item-1', 'title': 'Paper'}])
            return httpx.Response(200, text='@article{item-1, title={Paper}}')

        client = ZoteroClient(_config(), client=httpx.Client(transport=httpx.MockTransport(handler)))

        self.assertEqual(client.export_library('csljson')[0]['id'], 'item-1')
        self.assertIn('@article', client.export_library('bibtex'))
        with self.assertRaises(ValueError):
            client.export_library('atom')

    def test_disabled_local_api_has_actionable_error(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(403, text='disabled'))
        client = ZoteroClient(_config(), client=httpx.Client(transport=transport))

        with self.assertRaisesRegex(ZoteroLocalAPIError, 'Settings'):
            client.healthcheck()

    def test_maps_papers_and_writes_portable_exports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = ZoteroClient(_config(temp_dir))
            paper = _paper()

            payload = client.map_paper_to_item(paper)
            paths = client.export_documents([paper, {'source_type': 'policy'}])

            self.assertEqual(payload['itemType'], 'journalArticle')
            self.assertEqual(payload['DOI'], '10.1234/energy.1')
            self.assertIn('citekey', payload)
            self.assertIn('Citation Key:', payload['extra'])
            csl = json.loads(Path(paths['csl_json']).read_text(encoding='utf-8'))
            bibtex = Path(paths['bibtex']).read_text(encoding='utf-8')
            self.assertEqual(len(csl), 1)
            self.assertEqual(csl[0]['citation-key'], payload['citekey'])
            self.assertIn(f"@article{{{payload['citekey']},", bibtex)
            self.assertIn('author = {Alice Zhang and Bob Li}', bibtex)

    def test_citekey_is_deterministic(self):
        self.assertEqual(generate_citekey(_paper()), generate_citekey(_paper()))


def _config(export_directory='data/zotero'):
    return {
        'outputs': {
            'zotero': {
                'base_url': 'http://localhost:23119/api',
                'user_id': 0,
                'export_directory': export_directory,
            }
        }
    }


def _paper():
    return {
        'id': 'paper-1',
        'source_type': 'paper',
        'title': 'Energy Agent Coordination',
        'authors_or_orgs': ['Alice Zhang', 'Bob Li'],
        'summary': 'An energy-system embodied intelligence paper.',
        'published_at': '2026-07-01',
        'doi': '10.1234/energy.1',
        'url': 'https://doi.org/10.1234/energy.1',
        'tags': ['虚拟电厂'],
        'categories': ['eess.SY'],
    }


if __name__ == '__main__':
    unittest.main()
