"""Discovery contracts: authentication, fairness, cursor durability and evidence."""
import tempfile
import unittest
from pathlib import Path
import httpx
from src.sources.openalex_search_adapter import OpenAlexSearchAdapter
from src.sources.crossref_adapter import CrossrefAdapter


class OpenAlexSearchAdapterTests(unittest.TestCase):
    def test_transient_429_and_503_retry_then_finish(self):
        responses = [429, 503, 200]
        with tempfile.TemporaryDirectory() as root:
            adapter = OpenAlexSearchAdapter(self.config(root, max_attempts=3, search_terms=['energy']))
            adapter.client.close()
            def handler(request):
                code = responses.pop(0)
                return httpx.Response(code, headers={'Retry-After': '0'},
                    json={'results': [], 'meta': {'next_cursor': None}})
            adapter.client = httpx.Client(transport=httpx.MockTransport(handler))
            result = adapter.fetch_range('2020-01-01', '2020-01-31')
            adapter.close()
            self.assertEqual(result.status, 'complete')
            self.assertEqual(responses, [])

    def test_unchanged_cursor_with_new_results_is_valid(self):
        calls = []
        with tempfile.TemporaryDirectory() as root:
            adapter = OpenAlexSearchAdapter(self.config(root, max_pages_per_run=3, search_terms=['energy']))
            adapter.client.close()
            def handler(request):
                calls.append(request.url.params['cursor'])
                return httpx.Response(200, json={'results': [{'id': f'W{len(calls)}', 'title': 'Energy control',
                    'publication_date': '2020-01-03'}] if len(calls) < 3 else [],
                    'meta': {'next_cursor': 'same'}})
            adapter.client = httpx.Client(transport=httpx.MockTransport(handler))
            result = adapter.fetch_range('2020-01-01', '2020-01-31')
            adapter.close()
            self.assertEqual(calls, ['*', 'same', 'same'])
            self.assertEqual(result.status, 'complete')
            self.assertEqual(len(result.records), 2)

    def config(self, root, **settings):
        return {'paper_discovery': {'checkpoint_directory': root}, 'sources': {
            'openalex': {'api_key': 'test-key'}, 'openalex_search': {
                'search_terms': ['energy control', 'energy markets'], 'journal_search': False,
                'request_interval_seconds': 0, 'max_retry_delay_seconds': 0,
                'max_attempts': 1, 'max_pages_per_run': 2, **settings}}}

    def test_fair_resumable_paging_preserves_abstract_and_auth(self):
        calls = []
        def handler(request):
            self.assertEqual(request.headers['Authorization'], 'Bearer test-key')
            self.assertIn('from_publication_date:2020-01-01', request.url.params['filter'])
            term, cursor = request.url.params['search'], request.url.params['cursor']
            calls.append((term, cursor))
            return httpx.Response(200, json={'results': [{
                'id': 'https://openalex.org/W' + str(len(calls)),
                'title': term, 'publication_date': '2020-01-03', 'type': 'article',
                'abstract_inverted_index': {'Energy': [0], 'control': [1]},
                'referenced_works': ['https://openalex.org/W0'],
            }], 'meta': {'next_cursor': 'page2' if cursor == '*' else None}})
        with tempfile.TemporaryDirectory() as root:
            config = self.config(root)
            for expected in ['partial', 'complete']:
                adapter = OpenAlexSearchAdapter(config)
                adapter.client.close()
                adapter.client = httpx.Client(transport=httpx.MockTransport(handler))
                result = adapter.fetch_range('2020-01-01', '2020-01-31')
                adapter.close()
                self.assertEqual(result.status, expected)
                self.assertEqual(result.records[0]['abstract'], 'Energy control')
                self.assertEqual(result.records[0]['references'], ['https://openalex.org/W0'])
            self.assertEqual(calls, [('energy control', '*'), ('energy markets', '*'),
                                    ('energy control', 'page2'), ('energy markets', 'page2')])
            self.assertEqual(len(result.records), 4)

    def test_outage_retains_cursor_and_is_never_complete(self):
        with tempfile.TemporaryDirectory() as root:
            for status in (429, 503):
                adapter = OpenAlexSearchAdapter(self.config(root))
                adapter.client.close()
                adapter.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status)))
                result = adapter.fetch_range('2020-01-01', '2020-01-31')
                adapter.close()
                self.assertEqual(result.status, 'unavailable')
                self.assertTrue(result.errors)
            self.assertEqual(len(list(Path(root).rglob('*.json'))), 2)

    def test_crossref_is_independent_and_preserves_abstract(self):
        def handler(request):
            self.assertEqual(request.url.host, 'api.crossref.org')
            self.assertIn('until-pub-date:2020-01-31', request.url.params['filter'])
            return httpx.Response(200, json={'message': {'items': [{
                'DOI': '10.1000/A', 'title': ['Energy control'], 'type': 'journal-article',
                'abstract': '<jats:p>Original abstract</jats:p>', 'ISSN': ['1949-3053'],
                'container-title': ['IEEE Transactions on Smart Grid'],
                'published': {'date-parts': [[2020, 1, 3]]}}], 'next-cursor': 'unused'}})
        with tempfile.TemporaryDirectory() as root:
            adapter = CrossrefAdapter({'paper_discovery': {'checkpoint_directory': root}, 'sources': {
                'crossref': {'search_terms': ['energy control'], 'journal_search': False, 'request_interval_seconds': 0}}})
            adapter.client.close()
            adapter.client = httpx.Client(transport=httpx.MockTransport(handler))
            result = adapter.fetch_range('2020-01-01', '2020-01-31')
            adapter.close()
            self.assertEqual(result.status, 'complete')
            self.assertEqual(result.records[0]['doi'], '10.1000/a')
            self.assertEqual(result.records[0]['abstract'], 'Original abstract')
